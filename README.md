# Hermes Zalo Gateway

> 🔌 Cài đặt Zalo Personal Account làm cổng kết nối gateway trong [Hermes Agent](https://github.com/NousResearch/hermes-agent) — hoạt động real-time giống Telegram.

**👤 Tác giả:** [Tuấn Techla AI](https://www.facebook.com/TuanTechlaAi/) · [GitHub](https://github.com/tuantoha) · ☎️ 08 6789 6096

## ✨ Tính năng

### 🤖 Auto-Reply Real-time
- **Gateway native** — Tích hợp trực tiếp vào Hermes Gateway như 1 platform (`✓ zalo connected`)
- **Poll 9 nhóm cùng lúc** — Quét tin nhắn mới mỗi 5 giây, refresh danh sách nhóm mỗi 5 phút
- **AI tự động phản hồi** — Nhận tin nhắn → Hermes AI xử lý → Gửi câu trả lời vào đúng nhóm
- **Không giới hạn nhóm** — Theo dõi tất cả nhóm Zalo tài khoản đang tham gia

### 👥 Quản lý Nhóm & Thành viên (Admin)
- **Thêm/Xoá thành viên** — Chỉ cần user ID, xoá hàng loạt được
- **Chặn thành viên** — Block người dùng khỏi nhóm
- **Gửi tin nhắn riêng (DM)** — Nhắn trực tiếp đến từng thành viên
- **Mời lại qua link** — Tự động tạo link mời khi cần thêm lại thành viên đã xoá
- **Kiểm tra quyền** — Tự động phát hiện nhóm nào có quyền admin

### 📊 Phân tích & Báo cáo
- **Top người gửi** — Ai nói nhiều nhất trong N ngày qua
- **Thành viên im lặng** — Phát hiện ai lâu không tương tác (để nhắc nhở hoặc xoá)
- **Thống kê nhóm** — Tổng số tin nhắn, số thành viên tích cực, thời gian hoạt động
- **Lịch sử chat** — Đọc lại toàn bộ tin nhắn từ SQLite DB

### 🔧 MCP Server — 17 Tools
- **💬 Nhắn tin:** `send_message`, `send_dm`
- **👥 Quản lý:** `list_groups`, `group_info`, `list_members`, `add_member`, `remove_member`, `block_member`
- **📊 Phân tích:** `analyze_group`, `get_inactive_members`
- **📝 Lịch sử:** `get_history`, `db_sync`, `db_enable`, `listen`
- **🔐 Tài khoản:** `get_me`, `auth_status`, `auth_login_qr`

### 🚀 Cài đặt 1-click
- **Script tự động** — `install.sh` làm mọi thứ: cài openzca → QR login → copy adapter → sửa Hermes core → config → restart
- **Hermes Skill** — Load skill `zalo-personal-gateway` để agent khác tự cài đặt
- **Tương thích** — macOS & Linux, Node.js ≥ 22, Python ≥ 3.11

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

**17 MCP tools có sẵn:**

| Tool | Chức năng |
|------|-----------|
| **💬 Nhắn tin** | |
| `zalo_send_message` | Gửi tin nhắn text vào group |
| `zalo_send_dm` | Gửi tin nhắn riêng (DM) đến 1 người |
| **👥 Quản lý nhóm (admin)** | |
| `zalo_list_groups` | Danh sách 9 nhóm đang tham gia |
| `zalo_group_info` | Thông tin chi tiết 1 nhóm (tên, admin, quyền) |
| `zalo_list_members` | Danh sách thành viên trong nhóm |
| `zalo_add_member` | Thêm thành viên vào nhóm |
| `zalo_remove_member` | Xoá thành viên khỏi nhóm |
| `zalo_block_member` | Chặn thành viên |
| **📊 Phân tích** | |
| `zalo_analyze_group` | Phân tích nhóm: top người gửi, thống kê, thành viên im lặng |
| `zalo_get_inactive_members` | Tìm thành viên lâu không tương tác (để nhắc nhở/xoá) |
| **📝 Lịch sử** | |
| `zalo_get_history` | Lịch sử tin nhắn từ SQLite DB |
| `zalo_db_sync` | Đồng bộ tin nhắn mới về DB |
| `zalo_db_enable` | Bật SQLite DB |
| `zalo_listen` | Lắng nghe tin nhắn real-time |
| **🔐 Tài khoản** | |
| `zalo_get_me` | Thông tin tài khoản Zalo |
| `zalo_auth_status` | Kiểm tra trạng thái đăng nhập |
| `zalo_auth_login_qr` | Lấy QR code đăng nhập |

**Ví dụ sử dụng:**
```
# Phân tích nhóm "Trợ Lý tư vấn" trong 7 ngày
zalo_analyze_group group_id="2747350517158961481" days=7

# Tìm thành viên không tương tác 30 ngày
zalo_get_inactive_members group_id="2747350517158961481" days=30

# Xoá thành viên
zalo_remove_member group_id="2747350517158961481" user_ids=["6537355654795723984"]

# Gửi tin nhắn riêng
zalo_send_dm user_id="1213889493140221873" message="Xin chào!"
```

### Quyền Admin

Tài khoản Zalo đăng nhập sẽ tự động kiểm tra quyền admin từng nhóm:

| Nhóm | Members | Quyền |
|------|---------|-------|
| Trợ Lý tư vấn | 4 | ✅ Admin (thêm/xoá thành viên) |
| Các nhóm khác | 3-615 | 👀 Chỉ đọc + theo dõi |

> **Muốn có quyền admin ở nhóm khác?** Cần được trưởng nhóm chỉ định làm admin/phó nhóm.

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
- **☎️ Điện thoại:** 08 6789 6096

## 📄 License

MIT

## 🙏 Credits

- [openzca](https://github.com/darkamenosa/openzca) — Zalo CLI (darkamenosa)
- [zca-js](https://github.com/nhocconsr/zca-js) — Zalo API library
- [Hermes Agent](https://github.com/NousResearch/hermes-agent) — AI Agent framework (Nous Research)
