#!/usr/bin/env python3
"""Offline behavior tests: temporary profiles, fake S3, no real credentials/network."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('aoss_under_test', Path(__file__).with_name('aoss.py'))
a = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(a)


class ServiceError(Exception):
    def __init__(self, code):
        self.response = {'Error': {'Code': code}}
        super().__init__('raw exception containing a secret must never be printed')


class FakeS3:
    def __init__(self):
        self.objects = {}
        self.calls = []
        self.download_override = None

    def head_object(self, Bucket, Key):
        self.calls.append(('head', Bucket, Key))
        if Key not in self.objects:
            raise ServiceError('404')
        body, metadata = self.objects[Key]
        return {'ContentLength': len(body), 'Metadata': metadata}

    def upload_file(self, path, bucket, key, ExtraArgs):
        self.calls.append(('upload', bucket, key))
        self.objects[key] = (Path(path).read_bytes(), ExtraArgs.get('Metadata', {}))

    def download_file(self, bucket, key, path):
        self.calls.append(('download', bucket, key))
        body = self.objects[key][0] if self.download_override is None else self.download_override
        Path(path).write_bytes(body)

    def list_objects_v2(self, **kw):
        self.calls.append(('list', kw))
        all_keys = sorted(k for k in self.objects if k.startswith(kw['Prefix']))
        first = int(kw.get('ContinuationToken', '0'))
        # Artificial short pages exercise pagination even for small test sets.
        end = min(len(all_keys), first + min(2, kw['MaxKeys']))
        response = {'Contents': [{'Key': k, 'Size': len(self.objects[k][0])} for k in all_keys[first:end]],
                    'IsTruncated': end < len(all_keys)}
        if response['IsTruncated']:
            response['NextContinuationToken'] = str(end)
        return response

    def generate_presigned_url(self, *args, **kw):
        return 'https://example.invalid/file?X-Amz-Signature=SYNTHETIC-TEST-ONLY'


class BehaviorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='aoss-offline-test-')
        self.root = Path(self.tmp.name)
        self.env = patch.dict(os.environ, {'AOSS_CONFIG_HOME': str(self.root / 'config')}, clear=True)
        self.env.start()
        self.s3 = FakeS3()
        self.c = a.validate_config(dict(endpoint='https://aoss.example.invalid', bucket='test-bucket', prefix='course'))
        config, secret = a.profile_paths('test')
        a.private_write(config, json.dumps(self.c))
        a.private_write(secret, json.dumps(dict(access_key='SYNTHETIC-AK', secret_key='SYNTHETIC-SK')))

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def call(self, args):
        out = io.StringIO()
        with patch.object(a, 'client', return_value=self.s3), contextlib.redirect_stdout(out):
            rc = a.main(['--profile', 'test'] + args)
        return rc, json.loads(out.getvalue()), out.getvalue()

    def test_profile_cannot_escape_config_directory(self):
        with self.assertRaises(a.UserError):
            a.profile_paths('../other')

    def test_endpoint_rejects_secrets_query_http_and_bucket_hostname(self):
        for url in ['http://aoss.example.invalid', 'https://AK:SK@aoss.example.invalid',
                    'https://aoss.example.invalid/?signature=abc',
                    'https://test-bucket.aoss.example.invalid', 'https://aoss.example.invalid/path']:
            with self.subTest(url=url), self.assertRaises(a.UserError):
                a.validate_config(dict(endpoint=url, bucket='test-bucket'))

    def test_local_doctor_does_not_access_network_or_print_secret(self):
        rc, result, output = self.call(['doctor'])
        self.assertEqual(rc, 0)
        self.assertFalse(result['network_checked'])
        self.assertEqual(self.s3.calls, [])
        self.assertNotIn('SYNTHETIC-SK', output)

    def test_environment_pair_must_be_complete(self):
        os.environ['AOSS_ACCESS_KEY_ID'] = 'SYNTHETIC-AK'
        with self.assertRaises(a.UserError):
            a.credentials('test')

    def test_env_only_never_falls_back_to_saved_secret(self):
        with self.assertRaises(a.UserError):
            a.credentials('test', env_only=True)

    def test_read_only_doctor_uses_one_scoped_request(self):
        rc, result, _ = self.call(['doctor', '--online'])
        self.assertEqual(rc, 0)
        self.assertTrue(result['network_checked'])
        self.assertEqual(self.s3.calls, [('list', dict(Bucket='test-bucket', Prefix='course/', MaxKeys=1))])

    def test_list_paginates_and_respects_limit(self):
        self.s3.objects = {f'course/data/{i}': (b'a', {}) for i in range(8)}
        rc, result, _ = self.call(['list', '--prefix', 'data/', '--limit', '5'])
        self.assertEqual(rc, 0)
        self.assertEqual(len(result['objects']), 5)
        self.assertTrue(result['more_available'])
        self.assertEqual(len(self.s3.calls), 3)

    def test_upload_and_download_binary_hash_roundtrip(self):
        src = self.root / 'input.bin'
        src.write_bytes(bytes(range(256)) * 17)
        dest = self.root / 'download.bin'
        rc, result, _ = self.call(['upload', str(src), 'data.bin', '--sha256'])
        self.assertEqual(rc, 0)
        self.assertEqual(result['bytes'], src.stat().st_size)
        rc, result, _ = self.call(['download', 'data.bin', str(dest)])
        self.assertEqual(rc, 0)
        self.assertTrue(result['expected_sha256_matched'])
        self.assertEqual(src.read_bytes(), dest.read_bytes())

    def test_upload_existing_object_is_not_overwritten(self):
        self.s3.objects['course/data.bin'] = (b'old', {})
        src = self.root / 'input.bin'
        src.write_bytes(b'new')
        rc, _, _ = self.call(['upload', str(src), 'data.bin'])
        self.assertEqual(rc, 1)
        self.assertEqual(self.s3.objects['course/data.bin'][0], b'old')

    def test_permission_denial_is_not_treated_as_missing(self):
        with patch.object(self.s3, 'head_object', side_effect=ServiceError('403')):
            with self.assertRaises(ServiceError):
                a.head_optional(self.s3, 'test-bucket', 'key')

    def test_download_corruption_is_not_published(self):
        self.s3.objects['course/data.bin'] = (b'original', {'sha256': '0' * 64})
        dest = self.root / 'output.bin'
        rc, _, _ = self.call(['download', 'data.bin', str(dest)])
        self.assertEqual(rc, 1)
        self.assertFalse(dest.exists())
        self.assertEqual(list(self.root.glob('.aoss-download-*')), [])

    def test_download_default_preserves_existing_file(self):
        self.s3.objects['course/data.bin'] = (b'remote', {})
        dest = self.root / 'output.bin'
        dest.write_bytes(b'keep-me')
        rc, _, _ = self.call(['download', 'data.bin', str(dest)])
        self.assertEqual(rc, 1)
        self.assertEqual(dest.read_bytes(), b'keep-me')

    def test_presigned_url_goes_to_private_file_not_stdout(self):
        self.s3.objects['course/data.bin'] = (b'data', {})
        dest = self.root / 'link.txt'
        rc, _, text = self.call(['presign', 'data.bin', '--output', str(dest)])
        self.assertEqual(rc, 0)
        self.assertNotIn('X-Amz-Signature', text)
        self.assertIn('X-Amz-Signature', dest.read_text())
        if os.name == 'posix':
            self.assertEqual(dest.stat().st_mode & 0o777, 0o600)

    def test_sdk_errors_do_not_print_raw_exception(self):
        with patch.object(self.s3, 'list_objects_v2', side_effect=ServiceError('AccessDenied')):
            rc, result, text = self.call(['list'])
        self.assertEqual(rc, 1)
        self.assertEqual(result['service_code'], 'AccessDenied')
        self.assertNotIn('raw exception', text)

    @unittest.skipUnless(importlib.util.find_spec('boto3'), 'SDK integration needs setup.py dependencies')
    def test_real_sdk_configuration_and_stubbed_request(self):
        from botocore.stub import Stubber
        sdk = a.client('test', self.c)
        self.assertEqual(sdk.meta.config.signature_version, 's3v4')
        self.assertEqual(sdk.meta.config.s3['addressing_style'], 'virtual')
        self.assertEqual(sdk.meta.config.request_checksum_calculation, 'when_required')
        with Stubber(sdk) as stub:
            stub.add_response('head_object', {'ContentLength': 4},
                              {'Bucket': 'test-bucket', 'Key': 'course/data.bin'})
            self.assertEqual(sdk.head_object(Bucket='test-bucket', Key='course/data.bin')['ContentLength'], 4)
            stub.assert_no_pending_responses()
        url = sdk.generate_presigned_url('get_object', Params={'Bucket': 'test-bucket', 'Key': 'course/data.bin'},
                                         ExpiresIn=60)
        self.assertTrue(url.startswith('https://test-bucket.aoss.example.invalid/'))
        self.assertIn('X-Amz-Signature=', url)


if __name__ == '__main__':
    unittest.main(verbosity=2)
