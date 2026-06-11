# Hermes Zalo Gateway

> 🔌 Cài đặt Zalo Personal Account làm cổng kết nối gateway trong [Hermes Agent](https://github.com/NousResearch/hermes-agent) — hoạt động real-time giống Telegram.

**👤 Tác giả:** [Tuấn Techla AI](https://www.facebook.com/TuanTechlaAi/) · [GitHub](https://github.com/tuantoha)

## ✨ Tính năng

- ✅ **Real-time** — Nhận tin nhắn Zalo (DM + Group) → AI xử lý → Tự động phản hồi
- ✅ **Gateway native** — Hiển thị `✓ zalo connected` giống Telegram
- ✅ **DB polling** — Quét tin nhắn mới mỗi 5 giây
- ✅ **Group chat** — Hỗ trợ nhắn và phản hồi trong nhóm Zalo
- ✅ **MCP Server** — 9 MCP tools để gửi/nhận/lịch sử/nhóm
- ✅ **One-click install** — Script tự động toàn bộ quy trình

## 📦 Cài đặt nhanh

```bash
git clone https://github.com/<your-username>/hermes-zalo-gateway.git
cd hermes-zalo-gateway
chmod +x install.sh
./install.sh
```

Script sẽ tự động:
1. Kiểm tra môi trường (Node.js, Python)
2. Cài đặt `openzca` CLI
3. Hiển thị QR code → bạn quét bằng app Zalo
4. Bật SQLite DB + đồng bộ lịch sử
5. Copy adapter + sửa Hermes core (3 file)
6. Cấu hình `.env` + `config.yaml`
7. Khởi động lại gateway + verify

## 🏗️ Kiến trúc

```
Zalo Server ←→ openzca CLI ←→ zca-js
                    ↑
            Hermes ZaloAdapter (gateway/platforms/zalo.py)
                    ↑
            Hermes Gateway (poll DB mỗi 5s → AI → send)
```

## 📋 Yêu cầu

| Thành phần | Version |
|------------|---------|
| [Hermes Agent](https://github.com/NousResearch/hermes-agent) | latest |
| [Node.js](https://nodejs.org) | >= 22.13 |
| [Python](https://python.org) | >= 3.11 |
| [openzca](https://github.com/darkamenosa/openzca) | >= 0.1.59 |
| Tài khoản Zalo | cá nhân |

## 📁 Cấu trúc repo

```
hermes-zalo-gateway/
├── install.sh           # Script cài đặt 1-click
├── zalo_adapter.py      # Gateway adapter (copy vào gateway/platforms/)
├── zalo_mcp_server.py   # MCP server (tùy chọn, copy vào mcp-servers/)
├── SKILL.md             # Hermes skill (load qua /skill zalo-personal-gateway)
└── README.md            # File này
```

## 🚀 Cách dùng

### Qua Gateway (real-time, tự động)

Sau khi cài đặt, gateway sẽ tự động:
- Poll tin nhắn mới mỗi 5 giây
- AI xử lý và phản hồi tự động
- Hiển thị log: `grep zalo ~/.hermes/logs/gateway.log`

### Qua MCP Server (thủ công, linh hoạt)

Cài thêm MCP server:
```bash
cp zalo_mcp_server.py ~/.hermes/mcp-servers/zalo/server.py
hermes mcp add zalo --command python3 --args ~/.hermes/mcp-servers/zalo/server.py
```

9 MCP tools có sẵn:
| Tool | Chức năng |
|------|-----------|
| `zalo_send_message` | Gửi tin nhắn text |
| `zalo_listen` | Lắng nghe tin nhắn đến |
| `zalo_list_groups` | Danh sách nhóm |
| `zalo_get_history` | Lịch sử chat |
| `zalo_get_me` | Thông tin tài khoản |
| `zalo_db_enable` | Bật SQLite DB |
| `zalo_db_sync` | Đồng bộ lịch sử |
| `zalo_auth_status` | Kiểm tra đăng nhập |
| `zalo_auth_login_qr` | Lấy QR code |

### Qua Hermes Skill

```bash
hermes -s zalo-personal-gateway "Cài đặt Zalo gateway"
```

## 🔧 Troubleshooting

| Lỗi | Cách fix |
|-----|----------|
| `zalo failed to connect` | Xóa `__pycache__` → restart gateway |
| `Unauthorized user on zalo` | Thêm user ID vào `ZALO_ALLOWED_USERS` |
| `send() missing argument` | Đảm bảo zalo.py đúng phiên bản |
| Gateway không start (macOS) | Dùng `os.fork()` như trong install.sh |
| Không nhận tin nhắn mới | Adapter tự sync DB mỗi 5s |
| QR không hiển thị | Mở file: `open /tmp/zalo_qr.png` |

## 📞 Liên hệ

- **Facebook:** [Tuấn Techla AI](https://www.facebook.com/TuanTechlaAi/)
- **GitHub:** [@tuantoha](https://github.com/tuantoha)

## 📄 License

MIT

## 🙏 Credits

- [openzca](https://github.com/darkamenosa/openzca) — Zalo CLI (darkamenosa)
- [zca-js](https://github.com/nhocconsr/zca-js) — Zalo API library
- [Hermes Agent](https://github.com/NousResearch/hermes-agent) — AI Agent framework (Nous Research)
