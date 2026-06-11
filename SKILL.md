---
name: zalo-personal-gateway
description: Cài đặt Zalo Personal Account làm cổng kết nối gateway trong Hermes (giống Telegram) — dùng openzca CLI + adapter tự build. Hỗ trợ DM + Group chat real-time.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos, linux]
---

# Zalo Personal Gateway — Cài đặt cổng kết nối Zalo cho Hermes

## Mục tiêu
Cài đặt Zalo Personal Account thành một **platform gateway** trong Hermes, hoạt động real-time giống Telegram:
- Nhận tin nhắn Zalo (DM + Group) → AI xử lý → Tự động phản hồi
- Hiển thị `✓ zalo connected` trong gateway status
- DB polling mỗi 5 giây

## Kiến trúc
```
Zalo Server ←→ openzca CLI ←→ zca-js
                    ↑
            Hermes ZaloAdapter (gateway/platforms/zalo.py)
                    ↑
            Hermes Gateway (poll DB mỗi 5s → AI → send)
```

---

## Bước 0 — Kiểm tra môi trường

```bash
node --version        # Cần >= 22.13
python3 --version     # Cần >= 3.11
which npm
```

## Bước 1 — Cài đặt openzca CLI

```bash
npm install -g openzca@latest
openzca --version     # Phải >= 0.1.59
```

## Bước 2 — Đăng nhập Zalo (QR code)

```bash
openzca auth login --qr-path /tmp/zalo_qr.png
```

> 📱 Mở app Zalo trên điện thoại → quét mã QR hiển thị trong terminal.
> Nếu QR không hiển thị, mở file: `open /tmp/zalo_qr.png`

**Verify:**
```bash
openzca me info        # Phải hiển thị thông tin tài khoản
openzca group list     # Danh sách nhóm
openzca db enable      # Bật SQLite DB
openzca db sync all    # Đồng bộ lịch sử (chạy 1 lần)
```

## Bước 3 — Tạo Zalo Adapter cho Hermes

Tạo file `~/.hermes/hermes-agent/gateway/platforms/zalo.py` với nội dung từ file `references/zalo_adapter.py` đính kèm skill này.

## Bước 4 — Sửa Hermes Core (3 file)

### 4.1 — Thêm `Platform.ZALO` vào enum

Mở file `~/.hermes/hermes-agent/gateway/config.py`, tìm dòng:
```python
    YUANBAO = "yuanbao"
```
Thêm ngay sau đó:
```python
    ZALO = "zalo"
```

### 4.2 — Thêm Zalo vào `_apply_env_overrides`

Trong cùng file `config.py`, tìm section `# WhatsApp` (khoảng dòng 1340).
Thêm ngay trước `# Slack`:

```python
    # Zalo (personal account via openzca CLI)
    zalo_enabled = os.getenv("ZALO_ENABLED", "").lower() in {"true", "1", "yes"}
    if zalo_enabled:
        _enable_from_env(Platform.ZALO)
```

### 4.3 — Thêm Zalo vào `_create_adapter` factory

Mở file `~/.hermes/hermes-agent/gateway/run.py`, tìm:
```python
            return YuanbaoAdapter(config)

        return None
```
Thêm trước `return None`:
```python
        elif platform == Platform.ZALO:
            from gateway.platforms.zalo import ZaloAdapter
            return ZaloAdapter(config)
```

### 4.4 — Thêm Zalo vào authorization map

Mở file `~/.hermes/hermes-agent/gateway/authz_mixin.py`, tìm:
```python
            Platform.YUANBAO: "YUANBAO_ALLOWED_USERS",
        }
```
Thêm trước `}`:
```python
            Platform.ZALO: "ZALO_ALLOWED_USERS",
```

## Bước 5 — Cấu hình môi trường

Thêm vào `~/.hermes/.env`:

```bash
ZALO_ENABLED=true
ZALO_ALLOWED_USERS=<ZALO_USER_ID>
```

> Lấy `ZALO_USER_ID` từ output của `openzca me info` (trường `userId`).

## Bước 6 — Thêm `zalo: {}` vào config.yaml

Mở `~/.hermes/config.yaml`, tìm dòng `whatsapp: {}`, thêm ngay sau:
```yaml
zalo: {}
```

## Bước 7 — Xóa cache Python + Restart Gateway

```bash
# Xóa cache
find ~/.hermes/hermes-agent -name "__pycache__" -path "*zalo*" -exec rm -rf {} + 2>/dev/null
find ~/.hermes/hermes-agent -name "__pycache__" -path "*authz*" -exec rm -rf {} + 2>/dev/null

# Kill gateway cũ
pkill -9 -f "hermes_cli.main gateway" 2>/dev/null
sleep 3

# Start gateway với Zalo (dùng fork để detach)
python3 << 'PYEOF'
import subprocess, os, sys
env = os.environ.copy()
env['HERMES_HOME'] = os.path.expanduser('~/.hermes')
env['ZALO_ENABLED'] = 'true'
pid = os.fork()
if pid == 0:
    os.setsid()
    subprocess.Popen(
        [os.path.expanduser('~/.hermes/hermes-agent/venv/bin/python'),
         '-m', 'hermes_cli.main', '--profile', 'default',
         'gateway', 'run', '--replace'],
        env=env, stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        close_fds=True,
    )
    sys.exit(0)
else:
    print(f'Gateway PID: {pid}')
    os.waitpid(pid, 0)
PYEOF
```

## Bước 8 — Verify

```bash
sleep 15
grep "zalo\|Gateway running" ~/.hermes/logs/gateway.log | tail -5
```

**Kết quả mong đợi:**
```
[Zalo] Connected as <Tên> (<ID>)
[Zalo] DB poller started (interval=5s)
✓ zalo connected
Gateway running with 3 platform(s)
```

## Bước 9 — Test

1. Nhắn 1 tin vào group Zalo
2. Kiểm tra log: `grep "zalo.*inbound" ~/.hermes/logs/gateway.log | tail -3`
3. Phải thấy: `[Zalo] inbound: <user_id> -> <nội dung>...`
4. Vài giây sau: `response ready: platform=zalo ...`

---

## Troubleshooting

| Lỗi | Cách fix |
|-----|----------|
| "zalo failed to connect" | Xóa `__pycache__` → restart gateway |
| "Unauthorized user on zalo" | Thêm user ID vào `ZALO_ALLOWED_USERS` |
| "send() missing argument: text" | Đảm bảo zalo.py dùng param `content` |
| Gateway không start (macOS) | Dùng `os.fork()` như Bước 7 |
| Không nhận tin nhắn mới | Adapter tự sync DB mỗi 5s (đã có trong code) |

## Cấu trúc file

| File | Hành động |
|------|-----------|
| `gateway/platforms/zalo.py` | **TẠO MỚI** — Adapter chính |
| `gateway/config.py` | SỬA — `Platform.ZALO` + env enable |
| `gateway/run.py` | SỬA — Factory case |
| `gateway/authz_mixin.py` | SỬA — Allowlist mapping |
| `~/.hermes/config.yaml` | SỬA — `zalo: {}` |
| `~/.hermes/.env` | SỬA — `ZALO_ENABLED` + `ZALO_ALLOWED_USERS` |
