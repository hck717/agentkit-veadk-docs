"""MCP exposure of the Seedream invoice formatting agent.

Serves the `FormattingAgent` capability as an MCP server (streamable-http)
using `agentkit.apps.mcp_app.AgentkitMCPApp` (FastMCP). External tools /
clients can call the `format_invoice_image` tool over MCP.
"""

from __future__ import annotations

from agentkit.apps.mcp_app.mcp_app import AgentkitMCPApp

from agents.formatting_agent import FormattingAgent


class FormattingMCPApp(AgentkitMCPApp):
    def __init__(self, mock: bool = True):
        super().__init__()
        self._formatting_agent = FormattingAgent(mock=mock)
        self._register_tools()

    def _register_tools(self) -> None:
        agent = self._formatting_agent

        @self.agent_as_a_tool
        async def format_invoice_image(
            image_path: str,
            invoice_json: str,
            template: str = "clean_business_invoice",
        ) -> dict:
            """Reformat an invoice image into a clean template using Seedream.

            Args:
                image_path: Path to the original invoice image file.
                invoice_json: JSON string with extracted invoice fields
                    (invoice_number, date, vendor, amount, tax, currency, line_items).
                template: Layout template name (e.g. clean_business_invoice).

            Returns:
                dict: FormattedInvoice fields (status, formatted_image_url,
                    formatted_image_path, prompt, ...).
            """
            return await agent.format_invoice_image(image_path, invoice_json, template)
