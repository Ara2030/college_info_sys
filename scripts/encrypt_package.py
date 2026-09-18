# -*- coding: utf-8 -*-
"""
Шифрование пакета передачи ИС колледжа (AES-256).

Создаёт защищённый паролем ZIP-архив с исходным кодом и дампом базы данных.
Пароль передаётся получателю ОТДЕЛЬНЫМ каналом (не вместе с архивом!).

Использование:
    python scripts/encrypt_package.py                    # пароль генерируется
    python scripts/encrypt_package.py --password "МойПароль"
    python scripts/encrypt_package.py --dir dist --out secure

Требуется: pip install pyzipper
"""
import argparse
import hashlib
import os
import secrets
import string
import sys
from datetime import datetime
from pathlib import Path

try:
    import pyzipper
except ImportError:
    print('ОШИБКА: не установлена библиотека pyzipper.')
    print('Установите: pip install pyzipper')
    sys.exit(1)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def generate_password(length=20):
    """Генерирует стойкий пароль (буквы, цифры, символы)."""
    alphabet = string.ascii_letters + string.digits + '!@#$%^&*-_=+'
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def add_tree(zf, base_dir: Path, arc_prefix=''):
    """Добавляет каталог рекурсивно (кроме секретных и временных файлов)."""
    exclude_names = {'.env', '.venv', '__pycache__', 'logs', 'media',
                     'backups', 'dist', '.git', '.gigacode'}
    exclude_suffixes = {'.pyc', '.pyo'}
    count = 0
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in exclude_names]
        for name in files:
            path = Path(root) / name
            if name in exclude_names or path.suffix in exclude_suffixes:
                continue
            rel = path.relative_to(base_dir)
            arcname = f'{arc_prefix}{rel}'.replace('\\', '/')
            zf.write(path, arcname)
            count += 1
    return count


def main():
    parser = argparse.ArgumentParser(description='Шифрование пакета ИС колледжа')
    parser.add_argument('--password', '-p', default='',
                        help='Пароль (если не указан — будет сгенерирован)')
    parser.add_argument('--dir', default='dist',
                        help='Папка с файлами для шифрования (по умолчанию dist)')
    parser.add_argument('--out', default='',
                        help='Имя выходного архива (без расширения)')
    args = parser.parse_args()

    src_dir = PROJECT_ROOT / args.dir
    if not src_dir.exists():
        print(f'ОШИБКА: папка {src_dir} не найдена.')
        print('Сначала выполните: powershell -File scripts\\export_project.ps1')
        sys.exit(1)

    password = args.password or generate_password()
    generated = not args.password

    stamp = datetime.now().strftime('%Y-%m-%d')
    out_name = args.out or f'college_info_sys_SECURE_{stamp}'
    out_path = src_dir / f'{out_name}.zip'

    print('=' * 62)
    print('   ШИФРОВАНИЕ ПАКЕТА ПЕРЕДАЧИ (AES-256)')
    print('=' * 62)
    print(f'   Источник: {src_dir}')

    # --- Упаковка с шифрованием ---
    print('\n>> Создание защищённого архива...')
    total = 0
    with pyzipper.AESZipFile(out_path, 'w',
                             compression=pyzipper.ZIP_DEFLATED,
                             encryption=pyzipper.WZ_AES) as zf:
        zf.setpassword(password.encode('utf-8'))
        zf.setencryption(pyzipper.WZ_AES, nbits=256)

        # 1. Дамп базы данных (в корне)
        dump = src_dir / 'database_dump.sql'
        if dump.exists():
            zf.write(dump, 'database_dump.sql')
            total += 1
            print(f'   + database_dump.sql ({dump.stat().st_size // 1024} КБ)')

        # 2. Папка с исходным кодом (без секретов), отдельной папкой в архиве
        stage = src_dir / 'college_info_sys'
        if stage.exists():
            n = add_tree(zf, stage, arc_prefix='college_info_sys/')
            total += n
            print(f'   + college_info_sys/ ({n} файлов)')

    size_mb = out_path.stat().st_size / (1024 * 1024)

    # --- Контрольная сумма ---
    sha = hashlib.sha256(out_path.read_bytes()).hexdigest()

    print(f'\n>> Архив создан: {out_path.name} ({size_mb:.2f} МБ)')
    print(f'   Файлов внутри: {total}')
    print(f'   Шифрование: AES-256 (шифруются и содержимое, и имена файлов)')
    print()
    print('=' * 62)
    print('   ПАРОЛЬ АРХИВА (передать ОТДЕЛЬНЫМ каналом!)')
    print('=' * 62)
    print(f'   {password}')
    print()
    print('   Как передать безопасно:')
    print('   1) архив — через облако/флешку/мессенджер')
    print('   2) пароль — ДРУГИМ каналом (звонок, SMS, личная встреча)')
    print()
    print(f'   SHA-256 архива: {sha}')
    print('   (получатель может сверить: Get-FileHash archive.zip -Algorithm SHA256)')
    print('=' * 62)

    # Сохраняем пароль и хеш в отдельный файл для отправителя
    info_path = src_dir / f'{out_name}_ПАРОЛЬ_НЕ_ПЕРЕДАВАТЬ.txt'
    info_path.write_text(
        f'Архив: {out_path.name}\n'
        f'SHA-256: {sha}\n'
        f'Пароль: {password}\n'
        f'Создан: {datetime.now():%d.%m.%Y %H:%M}\n\n'
        'ВНИМАНИЕ: этот файл НЕ передавать вместе с архивом!\n'
        'Пароль сообщить получателю отдельным защищённым каналом.\n',
        encoding='utf-8')
    print(f'\n   Пароль и хеш сохранены в: {info_path.name}')
    print('   (этот файл оставить у себя, НЕ передавать с архивом)')

    if generated:
        print('\n   Пароль сгенерирован автоматически (20 символов).')


if __name__ == '__main__':
    main()
