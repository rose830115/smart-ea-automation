from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from yims_payload_builder import build_yims_extends_data, load_comments, write_yims_fill_plan


BASE_URL = "https://mrc.ycmproducts.com"
AUTH_STATE = Path(__file__).resolve().parent / ".yims_auth_state.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def import_playwright():
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit("缺少 Playwright。請先執行：python -m pip install playwright && python -m playwright install chromium") from exc
    return sync_playwright, PlaywrightTimeoutError


def visible_count(locator) -> int:
    try:
        return locator.count()
    except Exception:
        return 0


def goto_domcontentloaded(page, url: str) -> None:
    try:
        page.goto(url, wait_until="domcontentloaded")
    except Exception as exc:
        if "ERR_ABORTED" not in str(exc):
            raise


def is_logged_in(page, base_url: str) -> bool:
    if "/login" in page.url:
        return False
    if page.url.startswith(f"{base_url}/admin/"):
        return True
    return visible_count(page.get_by_text("登出", exact=True)) > 0


def ensure_login(page, context, args, PlaywrightTimeoutError) -> None:
    goto_domcontentloaded(page, f"{args.base_url}/admin/lab_admins/me")
    if is_logged_in(page, args.base_url):
        return

    account = os.getenv("YIMS_ACCOUNT") or os.getenv("YIMS_EMAIL")
    password = os.getenv("YIMS_PASSWORD")

    if account and password:
        goto_domcontentloaded(page, f"{args.base_url}/login")
        page.get_by_placeholder("帳號").fill(account)
        page.get_by_placeholder("密碼").fill(password)
        page.get_by_role("button", name="登入").click()
        page.wait_for_load_state("domcontentloaded")
    elif args.no_interactive_login:
        raise RuntimeError(
            "YIMS 尚未登入，網頁模式不會卡住等待手動輸入。"
            "請先在工具主機終端機執行一次 yims_bot.py 並手動登入，"
            "或設定 YIMS_ACCOUNT / YIMS_PASSWORD 環境變數。"
        )
    else:
        goto_domcontentloaded(page, f"{args.base_url}/login")
        print("YIMS 尚未登入。請在開啟的瀏覽器中手動登入，登入完成後回到終端機按 Enter。")
        input()

    deadline = time.time() + 30
    while time.time() < deadline:
        if is_logged_in(page, args.base_url):
            break
        time.sleep(0.5)
    else:
        raise RuntimeError("YIMS 登入未完成，無法繼續自動填表。")

    context.storage_state(path=str(args.auth_state))


def open_smart_ea_indoor_page(page, args, PlaywrightTimeoutError) -> None:
    goto_domcontentloaded(page, f"{args.base_url}/admin/orders/detail/{args.order_id}")
    try:
        page.wait_for_load_state("networkidle", timeout=30000)
    except PlaywrightTimeoutError:
        pass

    if visible_count(page.get_by_role("button", name="新增主區域資料")) == 0:
        test_result_button = page.get_by_role("button", name="測試結果")
        if visible_count(test_result_button) > 0:
            test_result_button.click(timeout=10000)

    english_button = page.get_by_role("button", name="英文")
    if visible_count(english_button) > 0:
        english_button.click(timeout=10000)

    try:
        if visible_count(page.locator("#inside-information-tab")) > 0:
            page.locator("#inside-information-tab").click(timeout=10000)
        else:
            page.get_by_text("室內", exact=True).click(timeout=10000)
    except PlaywrightTimeoutError:
        pass
    page.get_by_role("button", name="新增主區域資料").wait_for(timeout=30000)


def inject_extends_data(page, extends_data: dict[str, Any], save: bool) -> dict[str, Any]:
    script = """
    async ({ extendsData, save }) => {
      function findSmartEaVm() {
        function isSmartEaProxy(proxy) {
          return (
            proxy &&
            proxy.data &&
            proxy.data.extends_data &&
            Array.isArray(proxy.data.extends_data.main_area_array)
          );
        }

        function findFromVNode(vnode, seen = new Set()) {
          if (!vnode || typeof vnode !== 'object' || seen.has(vnode)) return null;
          seen.add(vnode);

          const component = vnode.component;
          if (component) {
            const proxy = component.proxy;
            if (isSmartEaProxy(proxy)) return proxy;

            const fromSubTree = findFromVNode(component.subTree, seen);
            if (fromSubTree) return fromSubTree;
          }

          const children = vnode.children;
          if (Array.isArray(children)) {
            for (const child of children) {
              const found = findFromVNode(child, seen);
              if (found) return found;
            }
          } else if (children && typeof children === 'object') {
            for (const child of Object.values(children)) {
              const found = findFromVNode(child, seen);
              if (found) return found;
            }
          }

          return null;
        }

        const appRoot = document.querySelector('#app');
        const fromAppRoot = appRoot && appRoot._vnode ? findFromVNode(appRoot._vnode) : null;
        if (fromAppRoot) return fromAppRoot;

        const nodes = Array.from(document.querySelectorAll('*'));
        for (const el of nodes) {
          let component = el.__vueParentComponent;
          while (component) {
            const proxy = component.proxy;
            if (isSmartEaProxy(proxy)) {
              return proxy;
            }
            component = component.parent;
          }
        }
        return null;
      }

      const vm = findSmartEaVm();
      if (!vm) {
        throw new Error('找不到 Smart EA Vue component，請確認目前位於 測試結果 / 英文 / 室內 頁面。');
      }

      vm.data.extends_data.analyze_parameter_selection = extendsData.analyze_parameter_selection || [];
      vm.data.extends_data.main_area_array = extendsData.main_area_array || [];
      if (vm.$forceUpdate) vm.$forceUpdate();
      if (vm.$nextTick) await vm.$nextTick();

      if (save) {
        await vm.save();
      }

      return {
        main_area_count: vm.data.extends_data.main_area_array.length,
        assessment_area_count: vm.data.extends_data.main_area_array
          .map((zone) => (zone.assessment_area_array || []).length)
          .reduce((sum, count) => sum + count, 0),
        saved: save,
      };
    }
    """
    return page.evaluate(script, {"extendsData": extends_data, "save": save})


def navigate_to_report_settings(page, args, PlaywrightTimeoutError) -> bool:
    """Try to navigate to the report settings tab/page. Returns True if successful."""
    try:
        # Try clicking a "報告設定" tab or button on the current page first
        for selector in [
            "button:has-text('報告設定')",
            "a:has-text('報告設定')",
            "[role='tab']:has-text('報告設定')",
            "li:has-text('報告設定')",
        ]:
            try:
                locator = page.locator(selector)
                if locator.count() > 0:
                    locator.first.click()
                    page.wait_for_load_state("domcontentloaded")
                    time.sleep(1)
                    return True
            except Exception:
                continue

        # Try direct URL patterns
        for suffix in ["/report_setting", "/report-setting", "?tab=report_setting"]:
            try:
                url = f"{args.base_url}/admin/orders/detail/{args.order_id}{suffix}"
                goto_domcontentloaded(page, url)
                time.sleep(1)
                # Check if there's useful content (look for risk table keywords)
                content = page.content()
                if "Environmental Mold Risk" in content or "Mold Risk" in content:
                    return True
            except Exception:
                continue
        return False
    except Exception:
        return False


def extract_risk_data_from_dom(page) -> dict[str, Any]:
    """Extract environmental and microbiology risk percentages from the report page DOM."""
    script = """
    () => {
        const result = {
            env_risk: { RMW: null, PL: null, FGW: null },
            micro_risk: { RMW: null, PL: null, FGW: null },
            env_params: {},
            raw_tables: []
        };

        // Find all tables on the page
        const tables = document.querySelectorAll('table');
        tables.forEach((table, tableIdx) => {
            const rows = table.querySelectorAll('tr');
            const tableData = [];
            rows.forEach(row => {
                const cells = row.querySelectorAll('td, th');
                tableData.push(Array.from(cells).map(c => c.innerText.trim()));
            });
            if (tableData.length > 0) result.raw_tables.push(tableData);

            // Find the env risk row
            rows.forEach(row => {
                const cells = Array.from(row.querySelectorAll('td, th'));
                const texts = cells.map(c => c.innerText.trim());
                const fullText = texts.join(' ');

                if (fullText.includes('Environmental Mold Risk')) {
                    // Expect: [label, RMW_val, PL_val, FGW_val] or similar
                    const nums = texts.slice(1).map(t => parseFloat(t)).filter(n => !isNaN(n));
                    if (nums.length >= 3) {
                        result.env_risk.RMW = nums[0];
                        result.env_risk.PL = nums[1];
                        result.env_risk.FGW = nums[2];
                    }
                }
                if (fullText.includes('Microbiological Mold Risk') || fullText.includes('Microbiology Mold Risk') || fullText.includes('Microbial Mold Risk')) {
                    const nums = texts.slice(1).map(t => parseFloat(t)).filter(n => !isNaN(n));
                    if (nums.length >= 3) {
                        result.micro_risk.RMW = nums[0];
                        result.micro_risk.PL = nums[1];
                        result.micro_risk.FGW = nums[2];
                    }
                }
            });
        });

        // Also try Vue component data
        function findRiskVm(node, seen = new Set()) {
            if (!node || typeof node !== 'object' || seen.has(node)) return null;
            seen.add(node);
            const comp = node.component;
            if (comp && comp.proxy) {
                const d = comp.proxy.data || comp.proxy.$data || {};
                if (d.env_risk || d.envRisk || d.environmentalMoldRisk) return comp.proxy;
            }
            const children = node.children;
            if (Array.isArray(children)) {
                for (const child of children) {
                    const found = findRiskVm(child, seen);
                    if (found) return found;
                }
            }
            return null;
        }
        const appRoot = document.querySelector('#app');
        if (appRoot && appRoot._vnode) {
            const vm = findRiskVm(appRoot._vnode);
            if (vm) {
                result.vue_data_keys = Object.keys(vm.data || vm.$data || {}).slice(0, 30);
            }
        }

        return result;
    }
    """
    try:
        return page.evaluate(script)
    except Exception as exc:
        return {"error": str(exc), "env_risk": {}, "micro_risk": {}}


def fetch_risk_data(page, args, PlaywrightTimeoutError, outdir: Path) -> dict[str, Any]:
    """Navigate to report settings, extract risk data, save as JSON, and take screenshot."""
    risk_screenshot = outdir / "99_logs" / f"yims_{args.order_id}_report_settings.png"
    risk_screenshot.parent.mkdir(parents=True, exist_ok=True)

    found = navigate_to_report_settings(page, args, PlaywrightTimeoutError)

    page.screenshot(path=str(risk_screenshot), full_page=True)
    dom_data = extract_risk_data_from_dom(page)

    risk_path = outdir / f"yims_{args.order_id}_risk_data.json"
    risk_path.write_text(
        json.dumps(dom_data, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )

    print(f"{'✓' if found else '⚠'} 報告設定頁面 {'已找到' if found else '未找到，請確認截圖'}：{risk_screenshot}")
    print(f"風險數據 JSON：{risk_path}")
    print(f"  env_risk:   {dom_data.get('env_risk', {})}")
    print(f"  micro_risk: {dom_data.get('micro_risk', {})}")

    dom_data["risk_screenshot"] = str(risk_screenshot)
    dom_data["risk_json_path"] = str(risk_path)
    return dom_data


def run_browser_fill(args: argparse.Namespace) -> dict[str, Any]:
    sync_playwright, PlaywrightTimeoutError = import_playwright()
    backend_payload = load_json(args.payload)
    comments = load_comments(args.metrics)
    extends_data = build_yims_extends_data(backend_payload, comments=comments)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless, slow_mo=args.slow_mo)
        context_kwargs = {}
        if args.auth_state.exists():
            context_kwargs["storage_state"] = str(args.auth_state)
        context = browser.new_context(**context_kwargs)
        page = context.new_page()
        page.on("dialog", lambda dialog: dialog.accept())

        ensure_login(page, context, args, PlaywrightTimeoutError)
        open_smart_ea_indoor_page(page, args, PlaywrightTimeoutError)
        result = inject_extends_data(page, extends_data, save=args.save)

        args.screenshot.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(args.screenshot), full_page=True)
        context.storage_state(path=str(args.auth_state))

        # After filling data, fetch risk numbers from report settings page
        outdir = args.screenshot.parent.parent
        risk_data = fetch_risk_data(page, args, PlaywrightTimeoutError, outdir)
        result["risk_data"] = risk_data

        if args.keep_open:
            print("YIMS 畫面已填入資料。請檢查後自行決定是否按「送出」。關閉瀏覽器後腳本才會結束。")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass

        browser.close()
        return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fill YIMS Smart EA page from backend payload")
    parser.add_argument("--payload", required=True, type=Path, help="*_backend_input_payload.json")
    parser.add_argument("--metrics", type=Path, help="*_environment_metrics.json, used for generated environmental comments")
    parser.add_argument("--order-id", help="YIMS order id / 案件代號")
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--auth-state", default=AUTH_STATE, type=Path)
    parser.add_argument("--screenshot", default=Path("logs/yims_filled_preview.png"), type=Path)
    parser.add_argument("--plan-json", type=Path, help="Write YIMS fill plan JSON and exit unless --order-id is also provided")
    parser.add_argument("--plan-md", type=Path, help="Write YIMS fill plan Markdown")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--slow-mo", default=80, type=int)
    parser.add_argument("--keep-open", action="store_true", help="Keep browser open for manual review")
    parser.add_argument("--save", action="store_true", help="Call YIMS save method after filling. Default is review-only.")
    parser.add_argument("--no-interactive-login", action="store_true", help="Fail instead of waiting for manual login input.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    backend_payload = load_json(args.payload)
    comments = load_comments(args.metrics)

    if args.plan_json or args.plan_md:
        plan_json = args.plan_json or args.payload.with_name(args.payload.name.replace("_backend_input_payload.json", "_yims_fill_plan.json"))
        plan_md = args.plan_md or args.payload.with_name(args.payload.name.replace("_backend_input_payload.json", "_yims_fill_plan.md"))
        write_yims_fill_plan(backend_payload, plan_json, plan_md, comments=comments)
        print(f"YIMS fill plan JSON: {plan_json}")
        print(f"YIMS fill plan Markdown: {plan_md}")
        if not args.order_id:
            return

    if not args.order_id:
        raise SystemExit("需要 --order-id 才能開 YIMS 填表。若只要產生計畫，請加 --plan-json 或 --plan-md。")

    result = run_browser_fill(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if not args.save:
        print("已填入 YIMS 畫面並截圖，但沒有按送出。若確認要儲存，請重新執行並加上 --save。")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
