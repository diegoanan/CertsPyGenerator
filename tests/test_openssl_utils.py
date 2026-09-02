import os
import tempfile

from certs_app.app import CertsPyGeneratorApp
from certs_app.openssl_utils import (
    build_bundle_filename,
    build_cert_filename,
    build_csr_filename,
    build_key_filename,
    generate_private_key,
    generate_csr,
    remove_key_password,
    verify_key_pair_match,
    normalize_certificate_file,
    concatenate_files,
)
from certs_app.storage import CertificateHistoryRepository


def test_generate_private_key_without_password():
    with tempfile.TemporaryDirectory() as tmpdir:
        key_path = os.path.join(tmpdir, 'server.key')
        generate_private_key(key_path, password=None, rsa_bits=2048)
        assert os.path.exists(key_path)
        with open(key_path, 'r', encoding='utf-8') as fh:
            text = fh.read()
        assert 'BEGIN PRIVATE KEY' in text or 'BEGIN ENCRYPTED PRIVATE KEY' in text


def test_build_filenames_for_key_csr_and_cert():
    assert build_key_filename('server', password=True).endswith('_pass.key')
    assert build_key_filename('server', password=False).endswith('_nopass.key')
    assert build_csr_filename('server').endswith('_req.csr')
    assert build_cert_filename('server').endswith(f'_cert_{2026}.pem')


def test_certificate_history_repository():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = CertificateHistoryRepository(os.path.join(tmpdir, 'history.db'))
        repo.add_entry('server', 'key', '/tmp/server_pass.key', 'generated')
        entries = repo.list_entries()
        assert len(entries) == 1
        assert entries[0]['name'] == 'server'


def test_generate_csr_and_remove_key_password():
    with tempfile.TemporaryDirectory() as tmpdir:
        key_path = os.path.join(tmpdir, 'server.key')
        csr_path = os.path.join(tmpdir, 'server.csr')
        subject = {
            'C': 'ES',
            'ST': 'Madrid',
            'L': 'Madrid',
            'O': 'CertsPyGenerator',
            'OU': 'DevOps',
            'CN': 'example.local',
        }

        generate_private_key(key_path, password='secret123', rsa_bits=2048)
        generate_csr(key_path, csr_path, subject, password='secret123')
        assert os.path.exists(csr_path)
        assert 'BEGIN CERTIFICATE REQUEST' in open(csr_path, 'r', encoding='utf-8').read()

        unencrypted_key = os.path.join(tmpdir, 'server_unencrypted.key')
        remove_key_password(key_path, unencrypted_key, password='secret123')
        assert os.path.exists(unencrypted_key)
        with open(unencrypted_key, 'r', encoding='utf-8') as fh:
            assert 'BEGIN PRIVATE KEY' in fh.read()


def test_verify_key_pair_match_for_key_and_csr():
    with tempfile.TemporaryDirectory() as tmpdir:
        key_path = os.path.join(tmpdir, 'server.key')
        csr_path = os.path.join(tmpdir, 'server.csr')
        subject = {
            'C': 'ES',
            'ST': 'Madrid',
            'L': 'Madrid',
            'O': 'CertsPyGenerator',
            'OU': 'DevOps',
            'CN': 'example.local',
        }
        generate_private_key(key_path, password='secret123', rsa_bits=2048)
        generate_csr(key_path, csr_path, subject, password='secret123')

        assert verify_key_pair_match(key_path, csr_path, password_a='secret123') is True


def test_verify_key_pair_match_and_normalize_certificate_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        key_path = os.path.join(tmpdir, 'key.pem')
        pub_path = os.path.join(tmpdir, 'pub.pem')
        generate_private_key(key_path, password=None, rsa_bits=2048)
        assert verify_key_pair_match(key_path, key_path) is True

        cert_path = os.path.join(tmpdir, 'cert.cer')
        with open(cert_path, 'wb') as fh:
            fh.write(b'-----BEGIN CERTIFICATE-----\r\nMIIB...\r\n-----END CERTIFICATE-----\r\n')
        normalized = normalize_certificate_file(cert_path)
        assert os.path.exists(normalized)


def test_build_bundle_filename_for_current_year():
    name = build_bundle_filename('combined')
    assert name.startswith('combined_cert_')
    assert name.endswith(f'_cert_{2026}.pem')

    cert_name = build_bundle_filename('combined', extension='.cert')
    assert cert_name.endswith(f'_cert_{2026}.cert')


def test_concatenate_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        first = os.path.join(tmpdir, 'a.txt')
        second = os.path.join(tmpdir, 'b.txt')
        output = os.path.join(tmpdir, 'combined.txt')

        with open(first, 'w', encoding='utf-8') as fh:
            fh.write('alpha\n')
        with open(second, 'w', encoding='utf-8') as fh:
            fh.write('beta\n')

        concatenate_files([first, second], output)
        assert os.path.exists(output)
        with open(output, 'r', encoding='utf-8') as fh:
            text = fh.read()
        assert 'alpha' in text and 'beta' in text


def test_repo_profile_is_applied_to_csr_subject_fields():
    app = CertsPyGeneratorApp()
    try:
        app.repo.add_subject({
            'name': 'perfil_prod',
            'C': 'ES',
            'ST': 'Madrid',
            'L': 'Madrid',
            'O': 'MiEmpresa',
            'OU': 'IT',
            'CN': 'api.example.local',
            'email': 'ops@example.local',
        })
        app._update_repo_combo()
        app.repo_select_var.set('perfil_prod')
        app._apply_subject_from_repo()

        assert app.csr_subject_fields['C'].get() == 'ES'
        assert app.csr_subject_fields['ST'].get() == 'Madrid'
        assert app.csr_subject_fields['CN'].get() == 'api.example.local'
        assert app.csr_subject_fields['email'].get() == 'ops@example.local'
    finally:
        app.destroy()
