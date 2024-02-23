import string
from pathlib import Path
from sanic import Sanic, file, html, redirect
from .database import Runbook, Section, Item, Run, Target


app = Sanic("listen")
root = Path(__file__).parent
with (root / "index.html").open() as f:
    INDEX = string.Template(f.read())


@app.on_response
async def default_response(request, response):
    if isinstance(response, str):
        return html(response)
    return response


@app.get("/")
async def index(request):
    return INDEX.substitute(autoload="/runbooks")


@app.get("/_/runbooks/<runbook_id>")
async def direct_runbook(request, runbook_id: int):
    return INDEX.substitute(autoload=f"/runbooks/{runbook_id}")


@app.get("/_/runs/<run_id>")
async def direct_run(request, run_id: int):
    return INDEX.substitute(autoload=f"/runs/{run_id}")


@app.get("/runbooks")
async def list_runbooks(request):
    return f"""
        {Runbook.load_input()}
        {"\n\n".join(f"{lst:link}" for lst in Runbook.all())}
        {Runbook.new_runbook_input()}
    """


@app.get("/runs")
async def list_runs(request):
    return "\n\n".join(f"{lst:link}" for lst in Run.all())


@app.get("/runbooks/<runbook_id>")
async def view_runbook(request, runbook_id: int):
    runbook = Runbook.from_id(runbook_id)
    return f"{runbook:detail}"


@app.post("/items/new/<section_id>")
async def new_item(request, section_id: int):
    name = request.form.get("name")
    section_id = int(section_id)
    item = Item.create(name=name, section_id=section_id)
    return f"""
        {item:detail}
        {Section.new_item_input(section_id, focus=True)}
    """


@app.post("/items/toggle/<item_id>")
async def toggle_item(request, item_id: int):
    item = Item.from_id(item_id)
    item.toggle()
    return f"{item:detail}"


@app.post("/items/change/<item_id>")
async def change_item(request, item_id: int):
    item = Item.from_id(item_id)
    name = request.form.get("name")
    if not name:
        item.delete()
        return ""
    else:
        item.rename(name)
        return f"{item:detail}"


@app.post("/sections/change/<section_id>")
async def change_section(request, section_id: int):
    section = Section.from_id(section_id)
    name = request.form.get("name")
    if not name:
        section.delete()
        return ""
    else:
        section.rename(name)
        return f"{section:detail}"


@app.post("/runbooks/change/<runbook_id>")
async def change_runbook(request, runbook_id: int):
    runbook = Runbook.from_id(runbook_id)
    name = request.form.get("name")
    if name:
        runbook.rename(name)
    return f"{runbook:heading}"


@app.post("/runbooks/load")
async def load_runbook(request):
    code = request.form.get("code")
    runbook = Runbook.load(code)
    return redirect(f"/runbooks/{runbook.id}")


@app.get("/runbooks/dump/<runbook_id>")
async def dump_runbook(request, runbook_id: int):
    runbook = Runbook.from_id(runbook_id)
    return f"""<script>
    window.prompt('Press Ctrl+C, Enter', '{runbook:dump_data}');
    </script>
    {runbook:dump_button}
    """


@app.post("/runs/change/<run_id>")
async def change_run(request, run_id: int):
    run = Run.from_id(run_id)
    name = request.form.get("name")
    if name:
        run.rename(name)
    return f"{run:heading}"


@app.post("/sections/new/<runbook_id>")
async def new_section(request, runbook_id: int):
    name = request.form.get("name")
    section = Section.create(name=name, runbook_id=runbook_id)
    return f"""
        {section:detail}
        {Runbook.new_section_input(runbook_id)}
    """


@app.post("/runs/new/<runbook_id>")
async def new_run(request, runbook_id: int):
    name = request.form.get("name")
    run = Run.create(runbook_id=runbook_id, name=name)
    return f"""
        <li>{run:link}</li>
        {Runbook.new_section_input(runbook_id)}
    """


@app.post("/runbooks/new")
async def new_runbook(request):
    name = request.form.get("name")
    runbook = Runbook.create(name=name)
    return f"""
        {runbook:link}
        {Runbook.new_runbook_input()}
    """


@app.get("/runs/<run_id>")
async def view_run(request, run_id: int):
    run = Run.from_id(run_id)
    return f"{run:detail}"


@app.post("/checkmarks/disable/<run_id>/<item_id>")
async def disable_checkmark(request, run_id: int, item_id: int):
    item = Item.from_id(item_id)
    run = Run.from_id(run_id)
    return item.check_for(run, disable=True)


@app.post("/checkmarks/disable/<run_id>/<item_id>/<target_id>")
async def disable_checkmark_for_target(
    request,
    run_id: int,
    item_id: int,
    target_id: int,
):
    item = Item.from_id(item_id)
    run = Run.from_id(run_id)
    return item.check_for(run, target_id=target_id, disable=True)


@app.post("/checkmarks/check/<run_id>/<item_id>")
async def check_checkmark(request, run_id: int, item_id: int):
    item = Item.from_id(item_id)
    run = Run.from_id(run_id)
    return item.check_for(run)


@app.post("/checkmarks/check/<run_id>/<item_id>/<target_id>")
async def check_checkmark_for_target(
    request,
    run_id: int,
    item_id: int,
    target_id: int,
):
    item = Item.from_id(item_id)
    run = Run.from_id(run_id)
    return item.check_for(run, target_id=target_id)


@app.post("/targets/new/<run_id>")
async def new_target(request, run_id: int):
    run = Run.from_id(run_id)
    name = request.form.get("name")
    Target.create(run_id=run.id, name=name)
    return f"{run:detail}"


@app.get("/vendor/htmx.min.js")
async def _htmx_js(request):
    return await file(root / "htmx.min.js")


@app.get("/vendor/Satisfy-Regular.woff2")
async def _satisfy_font(request):
    return await file(root / "Satisfy-Regular.woff2")


@app.get("/favicon.ico")
async def _favicon(request):
    return await file(root / "favicon.ico")
