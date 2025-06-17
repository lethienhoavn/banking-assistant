from langchain.tools import StructuredTool
from pydantic.v1 import BaseModel
import os


def write_report(filename, html):
    os.makedirs("reports", exist_ok=True)
    with open("reports/" + filename, 'w') as f:
        f.write(html)
    return html


class WriteReportArgsSchema(BaseModel):
    filename: str
    html: str


write_report_tool = StructuredTool.from_function(
    name="write_report",
    description="Write an HTML file to disk. Use this tool whenever someone asks for a report.",
    func=write_report,
    args_schema=WriteReportArgsSchema
)
