"""CLI entry point for the Facebook content agent.

Content is normally written by hand (or by Claude Code in chat) and passed
via --message; --topic/generate only apply if ANTHROPIC_API_KEY has credit.

Examples:
    python src/main.py post --message "Nội dung viết tay, đăng luôn"
    python src/main.py schedule --message "..." --time 2026-08-02T09:00
    python src/main.py schedule-batch --file data/content_plan_input.json
    python src/main.py list-posts
    python src/main.py insights
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config  # noqa: E402
from meta_client import MetaClient  # noqa: E402


def cmd_generate(args):
    from content_generator import ContentGenerator

    gen = ContentGenerator()
    text = gen.generate_post(args.topic, cta=args.cta)
    print(text)


def cmd_post(args):
    client = MetaClient()
    if args.message:
        message = args.message
    else:
        from content_generator import ContentGenerator

        gen = ContentGenerator()
        message = gen.generate_post(args.topic, cta=args.cta)
        print("--- Nội dung sinh ra ---")
        print(message)
        print("------------------------")
    if args.dry_run:
        print("(dry-run) Không đăng bài thật.")
        return
    result = client.post_text(message, link=args.link)
    print("Đã đăng:", result)


def cmd_schedule(args):
    if args.message:
        message = args.message
    else:
        from content_generator import ContentGenerator

        gen = ContentGenerator()
        message = gen.generate_post(args.topic, cta=args.cta)
        print("--- Nội dung sinh ra ---")
        print(message)
        print("------------------------")
    publish_dt = datetime.fromisoformat(args.time)
    client = MetaClient()
    result = client.schedule_post(message, publish_dt, link=args.link)
    print(f"Đã lên lịch đăng lúc {publish_dt}:", result)


def cmd_schedule_batch(args):
    from scheduler import schedule_batch

    entries = json.loads(Path(args.file).read_text(encoding="utf-8"))
    plan = schedule_batch(entries)
    print(f"Đã lên lịch {len(entries)} bài. Xem data/content_plan.json để theo dõi.")
    print(json.dumps(plan[-len(entries):], ensure_ascii=False, indent=2))


def cmd_list_posts(args):
    client = MetaClient()
    posts = client.list_recent_posts(limit=args.limit)
    for p in posts:
        print(f"{p.get('created_time')}  {p.get('id')}  {p.get('permalink_url')}")
        print(f"  {(p.get('message') or '')[:80]}")


def cmd_insights(args):
    client = MetaClient()
    metrics = args.metrics.split(",")
    data = client.get_page_insights(metrics, period=args.period)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def build_parser():
    parser = argparse.ArgumentParser(description="Facebook Content Agent (Toyota Đồng Tháp)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("generate", help="Sinh nội dung, chỉ in ra màn hình")
    p.add_argument("--topic", required=True)
    p.add_argument("--cta")
    p.set_defaults(func=cmd_generate)

    p = sub.add_parser("post", help="Sinh nội dung (hoặc dùng --message) rồi đăng ngay")
    p.add_argument("--topic")
    p.add_argument("--message")
    p.add_argument("--cta")
    p.add_argument("--link")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_post)

    p = sub.add_parser("schedule", help="Lên lịch đăng qua Facebook (nội dung tự viết hoặc Claude sinh)")
    p.add_argument("--topic", help="Chủ đề để Claude tự sinh nội dung (bỏ qua nếu dùng --message)")
    p.add_argument("--message", help="Nội dung viết sẵn, đăng nguyên văn")
    p.add_argument("--cta")
    p.add_argument("--link")
    p.add_argument("--time", required=True, help="ISO format, vd 2026-08-02T09:00")
    p.set_defaults(func=cmd_schedule)

    p = sub.add_parser("schedule-batch", help="Lên lịch hàng loạt từ file JSON")
    p.add_argument("--file", required=True, help='JSON: [{"topic":..., "publish_time":"YYYY-MM-DDTHH:MM"}]')
    p.set_defaults(func=cmd_schedule_batch)

    p = sub.add_parser("list-posts", help="Liệt kê bài đăng gần đây")
    p.add_argument("--limit", type=int, default=10)
    p.set_defaults(func=cmd_list_posts)

    p = sub.add_parser("insights", help="Xem chỉ số Page")
    p.add_argument("--metrics", default="page_views_total,page_post_engagements,page_total_actions")
    p.add_argument("--period", default="day")
    p.set_defaults(func=cmd_insights)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
