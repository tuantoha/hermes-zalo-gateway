#!/bin/bash
# ============================================================
# Hermes Zalo Gateway — One-click Installer
# ============================================================
# Cài đặt Zalo Personal Account làm cổng kết nối gateway
# trong Hermes, hoạt động real-time giống Telegram.
#
# Usage:
#   chmod +x install.sh
#   ./install.sh
# ============================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
HERMES_AGENT_DIR="$HERMES_HOME/hermes-agent"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo -e "${CYAN}============================================================${NC}"
echo -e "${CYAN}   Hermes Zalo Gateway — Cài đặt tự động${NC}"
echo -e "${CYAN}============================================================${NC}"
echo ""

# ---- Bước 1: Kiểm tra môi trường ----
echo -e "${YELLOW}[1/7] Kiểm tra môi trường...${NC}"

if ! command -v node &>/dev/null || [ "$(node -v | cut -d'v' -f2 | cut -d'.' -f1)" -lt 22 ]; then
    echo -e "${RED}❌ Cần Node.js >= 22.13. Cài đặt: brew install node${NC}"
    exit 1
fi
echo -e "  ${GREEN}✅ Node.js $(node -v)${NC}"

if ! command -v python3 &>/dev/null; then
    echo -e "${RED}❌ Cần Python >= 3.11${NC}"
    exit 1
fi
echo -e "  ${GREEN}✅ Python $(python3 -V | cut -d' ' -f2)${NC}"

# ---- Bước 2: Cài openzca ----
echo -e "${YELLOW}[2/7] Cài đặt openzca CLI...${NC}"

if ! command -v openzca &>/dev/null; then
    npm install -g openzca@latest
    echo -e "  ${GREEN}✅ openzca $(openzca --version) đã cài${NC}"
else
    echo -e "  ${GREEN}✅ openzca $(openzca --version) đã có sẵn${NC}"
fi

# ---- Bước 3: Đăng nhập Zalo ----
echo -e "${YELLOW}[3/7] Đăng nhập Zalo...${NC}"
echo -e "  ${CYAN}📱 Mở app Zalo trên điện thoại để quét mã QR bên dưới:${NC}"
echo ""

openzca auth login --qr-path /tmp/zalo_qr.png 2>/dev/null || {
    echo -e "${RED}❌ Đăng nhập thất bại. Thử lại: openzca auth login${NC}"
    exit 1
}

# Verify login
if ! openzca me info &>/dev/null; then
    echo -e "${RED}❌ Chưa đăng nhập Zalo${NC}"
    exit 1
fi

ZALO_USER_ID=$(openzca me info 2>/dev/null | grep "userId" | head -1 | sed "s/.*'\(.*\)'.*/\\1/")
ZALO_NAME=$(openzca me info 2>/dev/null | grep "displayName" | head -1 | sed "s/.*'\(.*\)'.*/\\1/")
echo -e "  ${GREEN}✅ Đã đăng nhập: $ZALO_NAME ($ZALO_USER_ID)${NC}"

# ---- Bước 4: Bật DB + sync ----
echo -e "${YELLOW}[4/7] Bật SQLite DB + đồng bộ lịch sử...${NC}"
openzca db enable 2>/dev/null || true
openzca db sync all 2>/dev/null || true
echo -e "  ${GREEN}✅ DB đã sẵn sàng${NC}"

# ---- Bước 5: Cài adapter vào Hermes ----
echo -e "${YELLOW}[5/7] Cài Zalo Adapter vào Hermes core...${NC}"

if [ ! -d "$HERMES_AGENT_DIR" ]; then
    echo -e "${RED}❌ Không tìm thấy Hermes agent tại $HERMES_AGENT_DIR${NC}"
    echo -e "${RED}   Đảm bảo Hermes đã được cài đặt.${NC}"
    exit 1
fi

# 5.1 — Copy adapter file
cp "$SCRIPT_DIR/zalo_adapter.py" "$HERMES_AGENT_DIR/gateway/platforms/zalo.py"
echo -e "  ${GREEN}✅ Đã copy gateway/platforms/zalo.py${NC}"

# 5.2 — Thêm Platform.ZALO vào config.py
if ! grep -q "ZALO = \"zalo\"" "$HERMES_AGENT_DIR/gateway/config.py"; then
    sed -i '' 's/    YUANBAO = "yuanbao"/    YUANBAO = "yuanbao"\n    ZALO = "zalo"/' "$HERMES_AGENT_DIR/gateway/config.py"
    echo -e "  ${GREEN}✅ Đã thêm Platform.ZALO vào config.py${NC}"
else
    echo -e "  ${GREEN}✅ Platform.ZALO đã có trong config.py${NC}"
fi

# 5.3 — Thêm Zalo env enable vào config.py
if ! grep -q "ZALO_ENABLED" "$HERMES_AGENT_DIR/gateway/config.py"; then
    ZALO_ENV_BLOCK='
    # Zalo (personal account via openzca CLI)
    zalo_enabled = os.getenv("ZALO_ENABLED", "").lower() in {"true", "1", "yes"}
    if zalo_enabled:
        _enable_from_env(Platform.ZALO)'
    sed -i '' "/# Slack/i\\
$ZALO_ENV_BLOCK
" "$HERMES_AGENT_DIR/gateway/config.py"
    echo -e "  ${GREEN}✅ Đã thêm Zalo env enable vào config.py${NC}"
else
    echo -e "  ${GREEN}✅ Zalo env enable đã có trong config.py${NC}"
fi

# 5.4 — Thêm Zalo vào run.py factory
if ! grep -q "Platform.ZALO" "$HERMES_AGENT_DIR/gateway/run.py"; then
    ZALO_FACTORY='        elif platform == Platform.ZALO:\n            from gateway.platforms.zalo import ZaloAdapter\n            return ZaloAdapter(config)'
    sed -i '' "/return YuanbaoAdapter(config)/a\\
$ZALO_FACTORY" "$HERMES_AGENT_DIR/gateway/run.py"
    echo -e "  ${GREEN}✅ Đã thêm Zalo factory vào run.py${NC}"
else
    echo -e "  ${GREEN}✅ Zalo factory đã có trong run.py${NC}"
fi

# 5.5 — Thêm Zalo vào authz_mixin.py
if ! grep -q "Platform.ZALO" "$HERMES_AGENT_DIR/gateway/authz_mixin.py"; then
    sed -i '' 's/Platform.YUANBAO: "YUANBAO_ALLOWED_USERS",/Platform.YUANBAO: "YUANBAO_ALLOWED_USERS",\n            Platform.ZALO: "ZALO_ALLOWED_USERS",/' "$HERMES_AGENT_DIR/gateway/authz_mixin.py"
    echo -e "  ${GREEN}✅ Đã thêm Zalo vào authz_mixin.py${NC}"
else
    echo -e "  ${GREEN}✅ Zalo authz đã có trong authz_mixin.py${NC}"
fi

# ---- Bước 6: Cấu hình env + config.yaml ----
echo -e "${YELLOW}[6/7] Cấu hình Hermes...${NC}"

# 6.1 — Thêm env vars
if ! grep -q "ZALO_ENABLED" "$HERMES_HOME/.env" 2>/dev/null; then
    cat >> "$HERMES_HOME/.env" <<EOF

# === Zalo Gateway ===
ZALO_ENABLED=true
ZALO_ALLOWED_USERS=$ZALO_USER_ID
EOF
    echo -e "  ${GREEN}✅ Đã thêm ZALO_ENABLED + ZALO_ALLOWED_USERS vào .env${NC}"
else
    echo -e "  ${GREEN}✅ Zalo env vars đã có trong .env${NC}"
fi

# 6.2 — Thêm zalo: {} vào config.yaml
if ! grep -q "^zalo:" "$HERMES_HOME/config.yaml" 2>/dev/null; then
    sed -i '' 's/^whatsapp: {}/whatsapp: {}\nzalo: {}/' "$HERMES_HOME/config.yaml"
    echo -e "  ${GREEN}✅ Đã thêm zalo: {} vào config.yaml${NC}"
else
    echo -e "  ${GREEN}✅ zalo: {} đã có trong config.yaml${NC}"
fi

# ---- Bước 7: Xóa cache + restart gateway ----
echo -e "${YELLOW}[7/7] Khởi động lại gateway...${NC}"

# Xóa cache
find "$HERMES_AGENT_DIR" -name "__pycache__" -path "*zalo*" -exec rm -rf {} + 2>/dev/null || true
find "$HERMES_AGENT_DIR" -name "__pycache__" -path "*authz*" -exec rm -rf {} + 2>/dev/null || true

# Kill gateway cũ
pkill -9 -f "hermes_cli.main gateway" 2>/dev/null || true
sleep 3

# Start gateway với Zalo
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

sleep 15

# Verify
echo ""
echo -e "${CYAN}============================================================${NC}"
echo -e "${CYAN}   Kết quả cài đặt${NC}"
echo -e "${CYAN}============================================================${NC}"

if grep -q "✓ zalo connected" "$HERMES_HOME/logs/gateway.log" 2>/dev/null; then
    echo -e "${GREEN}✅ Zalo Gateway đã kết nối thành công!${NC}"
    echo ""
    grep "zalo\|Gateway running" "$HERMES_HOME/logs/gateway.log" | tail -5
    echo ""
    echo -e "${GREEN}📱 Nhắn 1 tin vào group Zalo để test!${NC}"
else
    echo -e "${YELLOW}⚠️  Gateway đang khởi động...${NC}"
    echo -e "${YELLOW}   Kiểm tra: grep 'zalo' ~/.hermes/logs/gateway.log${NC}"
fi

echo ""
echo -e "${CYAN}Thông tin:${NC}"
echo -e "  Tài khoản: ${GREEN}$ZALO_NAME${NC}"
echo -e "  User ID:   ${GREEN}$ZALO_USER_ID${NC}"
echo -e "  Log:       ${GREEN}~/.hermes/logs/gateway.log${NC}"
echo ""
echo -e "${CYAN}Done! 🚀${NC}"
