import plotly.express as px
import pandas as pd
import uuid
import os
from langchain.tools import StructuredTool
from pydantic.v1 import BaseModel
from typing import List

# Create folder if needed
os.makedirs("charts", exist_ok=True)

def plot_chart(type, x, y, title="Chart"):
    df = pd.DataFrame({"x": x, "y": y})

    if type == "bar":
        fig = px.bar(df, x="x", y="y", title=title)
    elif type == "line":
        fig = px.line(df, x="x", y="y", title=title)
    else:
        return "Unsupported chart type"

    os.makedirs("charts", exist_ok=True)
    filename = f"{uuid.uuid4().hex}.png"
    filepath = os.path.join("charts", filename)
    fig.write_image(filepath)  # requires kaleido installed

    return filepath


class PlotChartArgs(BaseModel):
    type: str  # bar or line
    x: List[str]
    y: List[float]
    title: str = "Chart"


plot_chart_tool = StructuredTool.from_function(
    name="plot_chart",
    description="Draw a chart (bar or line) from x and y values and return path to image file.",
    func=plot_chart,
    args_schema=PlotChartArgs
)
