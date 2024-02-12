from urllib.parse import parse_qs
from robyn import Robyn
from robyn.templating import JinjaTemplate
from database import Runbook, Section, Item, Run, Target


app = Robyn(__file__)
T = JinjaTemplate(".")


@app.get("/", const=True)
async def index(request):
    return T.render_template("index.html", autoload="/runbooks")


@app.get("/_/runbooks/:runbook_id")
async def direct_runbook(request):
    runbook_id = int(request.path_params.get("runbook_id"))
    return T.render_template("index.html", autoload=f"/runbooks/{runbook_id}")


@app.get("/_/runs/:run_id")
async def direct_run(request):
    run_id = int(request.path_params.get("run_id"))
    return T.render_template("index.html", autoload=f"/runs/{run_id}")


@app.get("/runbooks")
async def list_runbooks(request):
    return f"""
        {"\n\n".join(f"{lst:link}" for lst in Runbook.all())}
        {Runbook.new_runbook_input()}
    """


@app.get("/runs")
async def list_runs(request):
    return "\n\n".join(f"{lst:link}" for lst in Run.all())


@app.get("/runbooks/:runbook_id")
async def view_runbook(request):
    runbook = Runbook.from_id(int(request.path_params.get("runbook_id")))
    return f"{runbook:detail}"


@app.post("/items/new/:section_id")
async def new_item(request):
    (name,) = parse_qs(request.body)["name"]
    section_id = int(request.path_params.get("section_id"))
    item = Item.create(name=name, section_id=section_id)
    return f"""
        {item:detail}
        {Section.new_item_input(section_id)}
    """


@app.post("/items/toggle/:item_id")
async def toggle_item(request):
    item = Item.from_id(int(request.path_params.get("item_id")))
    item.toggle()
    return f"{item:detail}"


@app.post("/items/change/:item_id")
async def change_item(request):
    item = Item.from_id(int(request.path_params.get("item_id")))
    body = parse_qs(request.body)
    names = body.get("name")
    if not names or not names[0]:
        item.delete()
        return ""
    else:
        name = names[0]
        item.rename(name)
        return f"{item:detail}"


@app.post("/sections/change/:section_id")
async def change_section(request):
    section = Section.from_id(int(request.path_params.get("section_id")))
    body = parse_qs(request.body)
    names = body.get("name")
    if not names or not names[0]:
        section.delete()
        return ""
    else:
        name = names[0]
        section.rename(name)
        return f"{section:detail}"


@app.post("/runbooks/change/:runbook_id")
async def change_runbook(request):
    runbook = Runbook.from_id(int(request.path_params.get("runbook_id")))
    body = parse_qs(request.body)
    names = body.get("name")
    if names and names[0]:
        name = names[0]
        runbook.rename(name)
    return f"{runbook:heading}"


@app.post("/runs/change/:run_id")
async def change_run(request):
    run = Run.from_id(int(request.path_params.get("run_id")))
    body = parse_qs(request.body)
    names = body.get("name")
    if names and names[0]:
        name = names[0]
        run.rename(name)
    return f"{run:heading}"


@app.post("/sections/new/:runbook_id")
async def new_section(request):
    (name,) = parse_qs(request.body)["name"]
    runbook_id = int(request.path_params.get("runbook_id"))
    section = Section.create(name=name, runbook_id=runbook_id)
    return f"""
        {section:detail}
        {Runbook.new_section_input(runbook_id)}
    """


@app.post("/runs/new/:runbook_id")
async def new_run(request):
    (name,) = parse_qs(request.body)["name"]
    runbook_id = int(request.path_params.get("runbook_id"))
    run = Run.create(runbook_id=runbook_id, name=name)
    return f"""
        <li>{run:link}</li>
        {Runbook.new_section_input(runbook_id)}
    """


@app.post("/runbooks/new")
async def new_runbook(request):
    (name,) = parse_qs(request.body)["name"]
    runbook = Runbook.create(name=name)
    return f"""
        {runbook:link}
        {Runbook.new_runbook_input()}
    """


@app.get("/runs/:run_id")
async def view_run(request):
    run = Run.from_id(int(request.path_params.get("run_id")))
    return f"{run:detail}"


@app.post("/checkmarks/check/:run_id/:item_id")
async def check_checkmark(request):
    item = Item.from_id(int(request.path_params.get("item_id")))
    run = Run.from_id(int(request.path_params.get("run_id")))
    return item.check_for(run)


@app.post("/checkmarks/check/:run_id/:item_id/:target_id")
async def check_checkmark_for_target(request):
    item = Item.from_id(int(request.path_params.get("item_id")))
    run = Run.from_id(int(request.path_params.get("run_id")))
    target_id = int(request.path_params.get("target_id"))
    return item.check_for(run, target_id=target_id)


@app.post("/targets/new/:run_id")
async def new_target(request):
    run = Run.from_id(int(request.path_params.get("run_id")))
    (name,) = parse_qs(request.body)["name"]
    Target.create(run_id=run.id, name=name)
    return f"{run:detail}"


@app.get("/vendor/htmx.min.js")
async def _htmx_js(request):
    return {
        "file_path": "./htmx.min.js",
        "headers": {
            "Content-Type": "text/javascript",
        },
    }


@app.get("/vendor/Satisfy-Regular.woff2")
async def _satisfy_font(request):
    return {
        "file_path": "./Satisfy-Regular.woff2",
        "headers": {
            "Content-Type": "application/font-woff2",
        },
    }


@app.get("/favicon.ico")
async def _favicon(request):
    return {
        "file_path": "./favicon.ico",
        "headers": {
            "Content-Type": "image/x-icon",
        },
    }


app.start(host="0.0.0.0", port=8080)
