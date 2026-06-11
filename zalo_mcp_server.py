#!/usr/bin/env python3
"""
MCP Server for Zalo Personal Account via openzca CLI.
Stdio JSON-RPC transport — compatible with Hermes MCP client.
"""
import json
import sys
import subprocess
import shlex
import os
from typing import Any

OPENZCA = "openzca"
PROFILE = os.environ.get("OPENZCA_PROFILE", "default")

def run_openzca(*args: str, timeout: int = 30, check: bool = True) -> dict:
    """Run openzca CLI and return parsed result."""
    cmd = [OPENZCA, "--profile", PROFILE] + list(args)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        output = r.stdout.strip()
        if r.returncode != 0 and check:
            return {"ok": False, "error": r.stderr.strip() or output, "exit_code": r.returncode}
        # Try JSON parse
        try:
            data = json.loads(output)
            if isinstance(data, dict):
                data.setdefault("ok", True)
                return data
            return {"ok": True, "data": data, "raw": output}
        except json.JSONDecodeError:
            return {"ok": True, "text": output}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"Timeout after {timeout}s"}
    except FileNotFoundError:
        return {"ok": False, "error": "openzca not found in PATH. Install: npm install -g openzca@latest"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# --- Tool definitions ---
TOOLS = [
    {
        "name": "zalo_auth_status",
        "description": "Kiểm tra trạng thái đăng nhập Zalo. Nếu chưa login, cần chạy 'openzca auth login' để quét QR.",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "zalo_auth_login_qr",
        "description": "Lấy QR code để đăng nhập Zalo. Trả về base64 QR image để hiển thị cho user scan.",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "zalo_send_message",
        "description": "Gửi tin nhắn văn bản đến một người dùng hoặc nhóm Zalo. Hỗ trợ markdown (**bold**, *italic*).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target_id": {"type": "string", "description": "ID người nhận hoặc group ID"},
                "message": {"type": "string", "description": "Nội dung tin nhắn"},
                "is_group": {"type": "boolean", "description": "True nếu gửi vào group", "default": False},
                "reply_to_msg_id": {"type": "string", "description": "ID tin nhắn cần reply (tùy chọn)"}
            },
            "required": ["target_id", "message"]
        }
    },
    {
        "name": "zalo_listen",
        "description": "Lắng nghe tin nhắn mới đến trong một khoảng thời gian ngắn (timeout giây). Trả về danh sách tin nhắn.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "timeout_seconds": {"type": "integer", "description": "Thời gian chờ tối đa (giây)", "default": 5}
            },
            "required": []
        }
    },
    {
        "name": "zalo_list_groups",
        "description": "Lấy danh sách nhóm Zalo mà tài khoản đang tham gia.",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "zalo_get_history",
        "description": "Lấy lịch sử tin nhắn từ SQLite DB của openzca. Cần chạy 'openzca db enable' và 'openzca db sync' trước.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "thread_id": {"type": "string", "description": "ID người dùng hoặc group"},
                "is_group": {"type": "boolean", "description": "True nếu là group chat", "default": False},
                "limit": {"type": "integer", "description": "Số tin nhắn tối đa", "default": 20}
            },
            "required": ["thread_id"]
        }
    },
    {
        "name": "zalo_get_me",
        "description": "Lấy thông tin tài khoản Zalo đang đăng nhập.",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "zalo_db_enable",
        "description": "Bật SQLite DB để lưu lịch sử tin nhắn (cần cho zalo_get_history).",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "zalo_db_sync",
        "description": "Đồng bộ lịch sử tin nhắn từ Zalo về SQLite DB.",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "zalo_group_info",
        "description": "Lấy thông tin chi tiết 1 nhóm: tên, mô tả, admin, số thành viên.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "group_id": {"type": "string", "description": "ID nhóm Zalo"}
            },
            "required": ["group_id"]
        }
    },
    {
        "name": "zalo_list_members",
        "description": "Lấy danh sách thành viên trong 1 nhóm Zalo.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "group_id": {"type": "string", "description": "ID nhóm Zalo"}
            },
            "required": ["group_id"]
        }
    },
    {
        "name": "zalo_add_member",
        "description": "Thêm thành viên vào nhóm Zalo (cần quyền admin/trưởng nhóm).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "group_id": {"type": "string", "description": "ID nhóm Zalo"},
                "user_ids": {"type": "array", "items": {"type": "string"}, "description": "Danh sách user ID cần thêm"}
            },
            "required": ["group_id", "user_ids"]
        }
    },
    {
        "name": "zalo_remove_member",
        "description": "Xoá thành viên khỏi nhóm Zalo (cần quyền admin/trưởng nhóm).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "group_id": {"type": "string", "description": "ID nhóm Zalo"},
                "user_ids": {"type": "array", "items": {"type": "string"}, "description": "Danh sách user ID cần xoá"}
            },
            "required": ["group_id", "user_ids"]
        }
    },
    {
        "name": "zalo_block_member",
        "description": "Chặn thành viên trong nhóm Zalo (cần quyền admin).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "group_id": {"type": "string", "description": "ID nhóm Zalo"},
                "user_id": {"type": "string", "description": "User ID cần chặn"}
            },
            "required": ["group_id", "user_id"]
        }
    },
    {
        "name": "zalo_send_dm",
        "description": "Gửi tin nhắn riêng (DM) đến 1 người dùng Zalo.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "User ID người nhận"},
                "message": {"type": "string", "description": "Nội dung tin nhắn"}
            },
            "required": ["user_id", "message"]
        }
    },
    {
        "name": "zalo_analyze_group",
        "description": "Phân tích tổng quan 1 nhóm: thành viên tích cực nhất, số tin nhắn, thời gian hoạt động, thành viên im lặng lâu.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "group_id": {"type": "string", "description": "ID nhóm Zalo"},
                "days": {"type": "integer", "description": "Số ngày phân tích (mặc định 7)", "default": 7}
            },
            "required": ["group_id"]
        }
    },
    {
        "name": "zalo_get_inactive_members",
        "description": "Tìm thành viên không tương tác trong N ngày qua để nhắc nhở hoặc xoá.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "group_id": {"type": "string", "description": "ID nhóm Zalo"},
                "days": {"type": "integer", "description": "Số ngày không tương tác (mặc định 30)", "default": 30}
            },
            "required": ["group_id"]
        }
    },
]

# --- Tool handlers ---
def handle_zalo_auth_status(args: dict) -> str:
    r = run_openzca("auth", "status")
    if r.get("ok"):
        return json.dumps(r, ensure_ascii=False)
    return json.dumps({"status": "not_logged_in", "hint": "Dùng zalo_auth_login_qr để lấy QR code đăng nhập", "detail": r}, ensure_ascii=False)

def handle_zalo_auth_login_qr(args: dict) -> str:
    import base64, tempfile
    qr_path = os.path.join(tempfile.gettempdir(), "zalo_qr.png")
    r = run_openzca("auth", "login", "--qr-path", qr_path, timeout=60)
    if os.path.exists(qr_path):
        with open(qr_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        os.remove(qr_path)
        return json.dumps({"ok": True, "qr_base64": b64, "hint": "Quét QR code bằng app Zalo trên điện thoại"}, ensure_ascii=False)
    return json.dumps(r, ensure_ascii=False)

def handle_zalo_send_message(args: dict) -> str:
    target = args["target_id"]
    msg = args["message"]
    cmd_args = ["msg", "send", target, msg]
    if args.get("is_group"):
        cmd_args.insert(3, "--group")
    if args.get("reply_to_msg_id"):
        cmd_args.extend(["--reply-id", args["reply_to_msg_id"]])
    r = run_openzca(*cmd_args)
    return json.dumps(r, ensure_ascii=False)

def handle_zalo_listen(args: dict) -> str:
    timeout = args.get("timeout_seconds", 5)
    r = run_openzca("listen", "--once", "--timeout", str(timeout), timeout=timeout + 10, check=False)
    return json.dumps(r, ensure_ascii=False)

def handle_zalo_list_groups(args: dict) -> str:
    r = run_openzca("group", "list", "--json")
    return json.dumps(r, ensure_ascii=False)

def handle_zalo_get_history(args: dict) -> str:
    thread_id = args["thread_id"]
    limit = args.get("limit", 20)
    cmd_args = ["db", "group", "messages", thread_id, "--json"]
    if args.get("is_group"):
        pass  # already correct
    if limit != 20:
        cmd_args.extend(["--limit", str(limit)])
    r = run_openzca(*cmd_args, check=False)
    return json.dumps(r, ensure_ascii=False)

def handle_zalo_get_me(args: dict) -> str:
    r = run_openzca("me", "info")
    return json.dumps(r, ensure_ascii=False)

def handle_zalo_db_enable(args: dict) -> str:
    r = run_openzca("db", "enable")
    return json.dumps(r, ensure_ascii=False)

def handle_zalo_db_sync(args: dict) -> str:
    r = run_openzca("db", "sync", timeout=120)
    return json.dumps(r, ensure_ascii=False)

def handle_zalo_group_info(args: dict) -> str:
    r = run_openzca("group", "info", args["group_id"])
    return json.dumps(r, ensure_ascii=False)

def handle_zalo_list_members(args: dict) -> str:
    r = run_openzca("group", "members", args["group_id"], "--json")
    return json.dumps(r, ensure_ascii=False)

def handle_zalo_add_member(args: dict) -> str:
    gid = args["group_id"]
    users = args["user_ids"]
    r = run_openzca("group", "add", gid, *users)
    return json.dumps(r, ensure_ascii=False)

def handle_zalo_remove_member(args: dict) -> str:
    gid = args["group_id"]
    users = args["user_ids"]
    r = run_openzca("group", "remove", gid, *users)
    return json.dumps(r, ensure_ascii=False)

def handle_zalo_block_member(args: dict) -> str:
    r = run_openzca("group", "block", args["group_id"], args["user_id"])
    return json.dumps(r, ensure_ascii=False)

def handle_zalo_send_dm(args: dict) -> str:
    r = run_openzca("msg", "send", args["user_id"], args["message"])
    return json.dumps(r, ensure_ascii=False)

def handle_zalo_analyze_group(args: dict) -> str:
    gid = args["group_id"]
    days = args.get("days", 7)
    # Sync DB first
    run_openzca("db", "sync", "group", gid, timeout=60)
    # Get messages
    r = run_openzca("db", "group", "messages", gid, "--json", "--limit", "500", check=False)
    if not r.get("ok") and "messages" not in r:
        return json.dumps(r, ensure_ascii=False)
    
    messages = r.get("messages", [])
    import time as _time
    cutoff = _time.time() * 1000 - days * 86400 * 1000
    
    member_stats = {}
    for m in messages:
        sid = str(m.get("senderId", ""))
        ts = int(m.get("ts", m.get("timestamp", 0)))
        if sid not in member_stats:
            member_stats[sid] = {"count": 0, "last_ts": 0, "name": m.get("senderName", sid)}
        member_stats[sid]["count"] += 1
        if ts > member_stats[sid]["last_ts"]:
            member_stats[sid]["last_ts"] = ts
    
    # Get member list
    members_r = run_openzca("group", "members", gid, "--json", check=False)
    all_members = members_r if isinstance(members_r, list) else members_r.get("members", [])
    
    inactive = []
    for m in all_members:
        uid = str(m.get("userId", ""))
        name = m.get("displayName", uid)
        if uid in member_stats:
            if member_stats[uid]["last_ts"] < cutoff:
                inactive.append({"userId": uid, "name": name, "last_active_days": round((_time.time()*1000 - member_stats[uid]["last_ts"])/86400000, 1)})
        else:
            inactive.append({"userId": uid, "name": name, "last_active_days": "never"})
    
    return json.dumps({
        "ok": True,
        "total_messages": len(messages),
        "active_members": len(member_stats),
        "total_members": len(all_members),
        "top_senders": sorted(member_stats.items(), key=lambda x: x[1]["count"], reverse=True)[:10],
        "inactive": inactive
    }, ensure_ascii=False)

def handle_zalo_get_inactive_members(args: dict) -> str:
    # Reuse analyze logic but return only inactive
    result = json.loads(handle_zalo_analyze_group(args))
    return json.dumps({
        "ok": True,
        "inactive": result.get("inactive", []),
        "total_members": result.get("total_members", 0)
    }, ensure_ascii=False)

HANDLERS = {
    "zalo_auth_status": handle_zalo_auth_status,
    "zalo_auth_login_qr": handle_zalo_auth_login_qr,
    "zalo_send_message": handle_zalo_send_message,
    "zalo_listen": handle_zalo_listen,
    "zalo_list_groups": handle_zalo_list_groups,
    "zalo_get_history": handle_zalo_get_history,
    "zalo_get_me": handle_zalo_get_me,
    "zalo_db_enable": handle_zalo_db_enable,
    "zalo_db_sync": handle_zalo_db_sync,
    "zalo_group_info": handle_zalo_group_info,
    "zalo_list_members": handle_zalo_list_members,
    "zalo_add_member": handle_zalo_add_member,
    "zalo_remove_member": handle_zalo_remove_member,
    "zalo_block_member": handle_zalo_block_member,
    "zalo_send_dm": handle_zalo_send_dm,
    "zalo_analyze_group": handle_zalo_analyze_group,
    "zalo_get_inactive_members": handle_zalo_get_inactive_members,
}

# --- MCP stdio loop ---
def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        
        req_id = req.get("id")
        method = req.get("method", "")
        params = req.get("params", {})
        
        if method == "initialize":
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "zalo-mcp", "version": "0.1.0"},
                    "capabilities": {"tools": {}}
                }
            }
        elif method == "tools/list":
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": TOOLS}
            }
        elif method == "tools/call":
            tool_name = params.get("name", "")
            tool_args = params.get("arguments", {})
            handler = HANDLERS.get(tool_name)
            if handler:
                try:
                    result_text = handler(tool_args)
                    resp = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [{"type": "text", "text": result_text}]
                        }
                    }
                except Exception as e:
                    resp = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [{"type": "text", "text": json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)}]
                        }
                    }
            else:
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}
                }
        elif method == "notifications/initialized":
            continue  # No response for notifications
        else:
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Unknown method: {method}"}
            }
        
        sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
        sys.stdout.flush()

if __name__ == "__main__":
    main()
