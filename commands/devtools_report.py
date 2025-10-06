"""Generate comprehensive DevTools report"""
from typing import Dict, Any
from .base import Command


class DevToolsReportCommand(Command):
    """Generate comprehensive DevTools debugging report"""

    @property
    def name(self) -> str:
        return "devtools_report"

    @property
    def description(self) -> str:
        return "⚠️ NO OUTPUT: Use save_page_info() instead - includes console + network data"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "include_dom": {"type": "boolean", "description": "Include DOM tree snapshot", "default": False}
            }
        }

    async def execute(self, include_dom: bool = False, console_logs=None) -> Dict[str, Any]:
        """Generate full DevTools report"""
        try:
            report = {
                "success": True,
                "timestamp": "",
                "console": [],
                "errors": [],
                "warnings": [],
                "network": {},
                "page_info": {},
                "dom": None
            }

            # Get page info
            page_info_js = """
            (function() {
                return {
                    url: window.location.href,
                    title: document.title,
                    readyState: document.readyState,
                    protocol: window.location.protocol,
                    host: window.location.host,
                    pathname: window.location.pathname,
                    userAgent: navigator.userAgent,
                    viewport: {
                        width: window.innerWidth,
                        height: window.innerHeight
                    },
                    performance: window.performance ? {
                        loaded: performance.timing.loadEventEnd > 0,
                        domReady: performance.timing.domContentLoadedEventEnd > 0,
                        navigationStart: performance.timing.navigationStart,
                        loadComplete: performance.timing.loadEventEnd
                    } : null
                };
            })()
            """
            page_result = self.tab.Runtime.evaluate(expression=page_info_js, returnByValue=True)
            report['page_info'] = page_result.get('result', {}).get('value', {})

            # Get console logs from CDP and JS interceptor
            cdp_logs = console_logs.copy() if console_logs else []

            # Get JS interceptor logs
            js_logs_code = """
            (function() {
                if (window.__consoleHistory) {
                    return window.__consoleHistory.slice();
                }
                return [];
            })()
            """
            js_logs_result = self.tab.Runtime.evaluate(expression=js_logs_code, returnByValue=True)
            js_logs = js_logs_result.get('result', {}).get('value', [])

            # Combine and categorize logs
            all_logs = []

            for log in cdp_logs:
                log_entry = {
                    "type": log.get("type", "log"),
                    "message": log.get("message", log.get("text", "")),
                    "timestamp": log.get("timestamp", ""),
                    "source": "cdp"
                }
                all_logs.append(log_entry)

                if log_entry["type"] == "error":
                    report["errors"].append(log_entry)
                elif log_entry["type"] == "warning":
                    report["warnings"].append(log_entry)

            for log in js_logs:
                log_entry = {
                    "type": log.get("type", "log"),
                    "message": log.get("message", ""),
                    "timestamp": log.get("timestamp", ""),
                    "source": "js-interceptor"
                }
                all_logs.append(log_entry)

                if log_entry["type"] == "error":
                    report["errors"].append(log_entry)
                elif log_entry["type"] == "warning":
                    report["warnings"].append(log_entry)

            report["console"] = all_logs

            # Get network activity
            network_js = """
            (function() {
                const entries = performance.getEntriesByType('resource');
                return {
                    total_requests: entries.length,
                    requests: entries.slice(-20).map(e => ({
                        name: e.name,
                        type: e.initiatorType,
                        duration: Math.round(e.duration),
                        size: e.transferSize || 0,
                        startTime: Math.round(e.startTime)
                    })),
                    failed: entries.filter(e => e.responseStatus === 0 || e.responseStatus >= 400).length
                };
            })()
            """
            network_result = self.tab.Runtime.evaluate(expression=network_js, returnByValue=True)
            report["network"] = network_result.get('result', {}).get('value', {})

            # Get DOM snapshot if requested
            if include_dom:
                dom_js = """
                (function() {
                    function getNodeInfo(node, depth = 0, maxDepth = 3) {
                        if (depth > maxDepth || !node) return null;

                        const info = {
                            tag: node.tagName,
                            id: node.id,
                            classes: Array.from(node.classList || []),
                            attributes: {},
                            children: []
                        };

                        if (node.attributes) {
                            for (let attr of node.attributes) {
                                info.attributes[attr.name] = attr.value;
                            }
                        }

                        if (depth < maxDepth) {
                            for (let child of node.children || []) {
                                const childInfo = getNodeInfo(child, depth + 1, maxDepth);
                                if (childInfo) info.children.push(childInfo);
                            }
                        }

                        return info;
                    }

                    return getNodeInfo(document.body, 0, 2);
                })()
                """
                dom_result = self.tab.Runtime.evaluate(expression=dom_js, returnByValue=True)
                report["dom"] = dom_result.get('result', {}).get('value')

            # Summary
            report["summary"] = {
                "total_console_logs": len(all_logs),
                "total_errors": len(report["errors"]),
                "total_warnings": len(report["warnings"]),
                "network_requests": report["network"].get("total_requests", 0),
                "network_failed": report["network"].get("failed", 0),
                "page_loaded": report["page_info"].get("readyState") == "complete"
            }

            return report

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to generate DevTools report: {str(e)}",
                "error": str(e)
            }
