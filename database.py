import base64
import gzip
import json
import psycopg
from psycopg.rows import dict_row


DB_SPEC = "dbname=listen user=jo"


class Entity:
    def __init__(self, row):
        self.__dict__.update(row)

    def __init_subclass__(cls):
        cls.table_name = cls.__name__.lower() + "s"

    @classmethod
    def from_id(cls, id):
        with psycopg.connect(DB_SPEC, row_factory=dict_row) as conn:
            return cls(
                conn.execute(
                    f"SELECT * FROM {cls.table_name} WHERE id=%(id)s",
                    {"id": id},
                ).fetchone()
            )

    @classmethod
    def all(cls):
        with psycopg.connect(DB_SPEC, row_factory=dict_row) as conn:
            return [cls(row) for row in conn.execute(f"SELECT * FROM {cls.table_name}")]

    @classmethod
    def create(cls, **kwargs):
        with psycopg.connect(DB_SPEC, row_factory=dict_row) as conn:
            return cls(
                conn.execute(
                    f"""
                        INSERT INTO {cls.table_name} ({', '.join(kwargs)})
                        VALUES ({', '.join(f"%({name})s" for name in kwargs)})
                        RETURNING *
                    """,
                    kwargs,
                ).fetchone()
            )

    def delete(self):
        with psycopg.connect(DB_SPEC, row_factory=dict_row) as conn:
            conn.execute(
                f"""
                    DELETE FROM {self.table_name}
                    WHERE id=%(id)s
                """,
                {
                    "id": self.id,
                },
            )

    def mutate(self, **kwargs):
        with psycopg.connect(DB_SPEC, row_factory=dict_row) as conn:
            self.__dict__.update(
                conn.execute(
                    f"""
                        UPDATE {self.table_name}
                        SET {", ".join(f"{name}=%({name})s" for name in kwargs)}
                        WHERE id=%(id)s
                        RETURNING *
                    """,
                    {
                        "id": self.id,
                        **kwargs,
                    },
                ).fetchone()
            )

    @classmethod
    def query(cls, order_by="id", **kwargs):
        with psycopg.connect(DB_SPEC, row_factory=dict_row) as conn:
            return [
                cls(row)
                for row in conn.execute(
                    f"""
                        SELECT *
                        FROM {cls.table_name}
                        WHERE {", ".join(f"{name}=%({name})s" for name in kwargs)}
                        ORDER BY {order_by}
                    """,
                    kwargs,
                )
            ]


class Runbook(Entity):
    def rename(self, new_name):
        self.mutate(name=new_name)

    @property
    def sections(self):
        return Section.query(runbook_id=self.id, order_by="rank ASC")

    @staticmethod
    def new_section_input(id):
        return f"""<input
            type="text"
            name="name"
            placeholder="New section"
            hx-swap="outerHTML"
            hx-post="/sections/new/{id}"
        >
        """

    @staticmethod
    def new_run_input(id):
        return f"""<input
            type="text"
            name="name"
            placeholder="New run"
            hx-swap="outerHTML"
            hx-post="/runs/new/{id}"
        >
        """

    @staticmethod
    def new_runbook_input():
        return """<input
            type="text"
            name="name"
            placeholder="New runbook"
            hx-swap="outerHTML"
            hx-post="/runbooks/new"
        >
        """

    @property
    def runs(self):
        return Run.query(runbook_id=self.id)

    def __format__(self, fmt):
        if fmt == "link":
            return f"""
                <a
                    class="label actionable"
                    hx-get="/runbooks/{self.id}"
                    hx-target="#container"
                    hx-push-url="/_/runbooks/{self.id}"
                >
                    {self.name}
                </a>
                {self:runs}

            </div>
            """
        elif fmt == "runs":
            return f"""
                <ul>
                    {"".join(f"<li>{run:link}</li>" for run in self.runs)}
                    {self.new_run_input(self.id)}
                </ul>
            """
        elif fmt == "heading":
            return f"""
            <h1
                hx-post="/runbooks/change/{self.id}"
                hx-swap="none"
                hx-trigger="input"
                hx-vals="js:name:event.target.innerHTML"
                class="editable"
                contenteditable
            >{self.name}</h1>
            """

        elif fmt == "dump_button":
            return f"""<a
                hx-get="/runbooks/dump/{self.id}"
                class="top-right large-icon actionable"
            >📋</a>"""
        elif fmt == "detail":
            return f"""
            <a class="noprint" href="/">↰ Runbooks</a><br>
            {self:heading}
            {self:dump_button}

            {"\n".join(f"{section:detail}" for section in self.sections)}

            {self.new_section_input(self.id)}

            <hr>
            {self:runs}
            """
        elif fmt == "dump_data":
            return base64.b85encode(
                b"\x00" + gzip.compress(
                    json.dumps(self.dump(), ensure_ascii=True).encode("utf-8"),
                ),
            ).decode("utf-8")
        else:
            raise f"unknown format code {fmt}"

    def dump(self):
        return [self.name, [section.dump() for section in self.sections]]

    @classmethod
    def load(cls, code):
        a = base64.b85decode(code)
        version, b = a[0], a[1:]
        assert version == 0
        name, sections = json.loads(gzip.decompress(b).decode("utf-8"))
        runbook = cls.create(name=name)
        for section_name, items in sections:
            section = Section.create(name=section_name, runbook_id=runbook.id)
            for name, type in items:
                Item.create(name=name, type=type, section_id=section.id)
        return runbook

    @staticmethod
    def load_input():
        return """<input
            hx-post="/runbooks/load"
            hx-target="#container"
            hx-trigger="keydown[key=='Enter']"
            class="top-right"
            name="code"
            placeholder="Enter share code"
        >"""


class Section(Entity):
    @property
    def items(self):
        return Item.query(section_id=self.id, order_by="rank ASC")

    def rename(self, new_name):
        self.mutate(name=new_name)

    @staticmethod
    def new_item_input(id, focus=False):
        return f"""<input
            type="text"
            name="name"
            placeholder="New item"
            hx-swap="outerHTML"
            hx-post="/items/new/{id}"
            {"autofocus" if focus else ""}
        >"""

    def __format__(self, fmt):
        if fmt == "heading":
            return f"""
            <h2
                hx-post="/sections/change/{self.id}"
                hx-swap="none"
                hx-trigger="input"
                hx-vals="js:name:event.target.innerHTML"
                class="editable"
                contenteditable
            >{self.name}</h2>
            """

        elif fmt == "detail":
            return f"""
            <section>
            {self:heading}

            <ul>
            {"\n".join(f"{item:detail}" for item in self.items)}
            {self:additem}
            </ul>
            </section>
            """
        elif fmt == "additem":
            return self.new_item_input(self.id)

    def dump(self):
        return [self.name, [item.dump() for item in self.items]]


class Item(Entity):
    def __format__(self, fmt):
        if fmt == "detail":
            return f"""
                <li>
                    <span
                        hx-post="/items/toggle/{self.id}"
                        hx-swap="outerHTML"
                        hx-target="closest li"
                        class="actionable type type-{self.type}"
                    >{self:type}</span>
                    <span
                        hx-post="/items/change/{self.id}"
                        hx-swap="none"
                        hx-trigger="input"
                        hx-vals="js:name:event.target.innerHTML"
                        class="editable"
                        contenteditable
                    >{self.name}</span>
                </li>
            """
        elif fmt == "type":
            if self.type == "each":
                return "∀"
            return "1"

    @staticmethod
    def css_classes(check_state):
        if check_state is None:
            return "unchecked actionable"
        elif check_state == "normal":
            return "checked actionable"
        else:
            return "disabled"

    def as_checkbox(self, run, checked):
        # checked is a dict like {None: "normal"|"not applicable"}
        if self.type == "once":
            classes = self.css_classes(checked.get(None))

            return f"""
                <li
                    hx-post="/checkmarks/check/{run.id}/{self.id}"
                    hx-swap="outerHTML"
                    hx-trigger="click[!ctrlKey]"
                    class="{classes}"
                >{self.name}
                    <span
                        hx-post="/checkmarks/disable/{run.id}/{self.id}"
                        hx-swap="outerHTML"
                        hx-target="closest li"
                        hx-trigger="click[ctrlKey] from:closest li"
                    ></span>
                </li>
            """
        else:
            if len(checked) == len(run.targets):
                extra_class = " checked"
            else:
                extra_class = ""
            return f"""
                <li class="multi{extra_class}">{self.name}
                <ul>
                {"\n".join(
                    f'''<li
                        class="{self.css_classes(checked.get(target.id))}"
                        hx-post="/checkmarks/check/{run.id}/{self.id}/{target.id}"
                        hx-swap="outerHTML"
                        hx-target="closest li.multi"
                        hx-trigger="click[!ctrlKey]"
                    >
                    <span
                        hx-post="/checkmarks/disable/{run.id}/{self.id}/{target.id}"
                        hx-swap="outerHTML"
                        hx-target="closest li.multi"
                        hx-trigger="click[ctrlKey] from:(closest li)"
                    ></span>
                    <div
                        class="multilabel target target-{i}"
                    >{target.name}</div></li>'''
                    for i, target in enumerate(run.targets)
                )}
                </ul>
                </li>
            """

    def toggle(self):
        new_type = "once" if self.type == "each" else "each"
        self.mutate(type=new_type)

    def check_for(self, run, target_id=None, disable=False):
        type = "not applicable" if disable else "normal"
        with psycopg.connect(DB_SPEC, row_factory=dict_row) as conn:
            checked_target_ids = [
                row["target_id"]
                for row in conn.execute(
                    """
                        SELECT *
                        FROM checkmarks
                        WHERE run_id=%(run_id)s AND item_id=%(item_id)s
                    """,
                    {"run_id": run.id, "item_id": self.id},
                ).fetchall()
            ]
            if self.type == "once":
                if checked_target_ids:
                    conn.execute(
                        f"""
                            DELETE FROM checkmarks
                            WHERE run_id=%(run_id)s AND item_id=%(item_id)s
                            {"" if disable else "AND type <> 'not applicable'"}
                        """,
                        {"run_id": run.id, "item_id": self.id},
                    )
                else:
                    conn.execute(
                        """
                            INSERT INTO checkmarks (run_id, item_id, type)
                            VALUES (%(run_id)s, %(item_id)s, %(type)s)
                        """,
                        {
                            "run_id": run.id,
                            "item_id": self.id,
                            "type": type,
                        },
                    )
            else:
                if target_id in checked_target_ids:
                    conn.execute(
                        f"""
                            DELETE FROM checkmarks
                            WHERE run_id=%(run_id)s
                                AND item_id=%(item_id)s
                                AND target_id=%(target_id)s
                            {"" if disable else "AND type <> 'not applicable'"}
                        """,
                        {
                            "run_id": run.id,
                            "item_id": self.id,
                            "target_id": target_id,
                        },
                    )
                else:
                    conn.execute(
                        """
                            INSERT INTO checkmarks (run_id, item_id, target_id, type)
                            VALUES (%(run_id)s, %(item_id)s, %(target_id)s, %(type)s)
                        """,
                        {
                            "run_id": run.id,
                            "item_id": self.id,
                            "target_id": target_id,
                            "type": type,
                        },
                    )
            conn.commit()
            return self.as_checkbox(run, run.get_checked().get(self.id, {}))

    def rename(self, new_name):
        self.mutate(name=new_name)

    def dump(self):
        return [self.name, self.type]


class Run(Entity):
    def __format__(self, fmt):
        if fmt == "link":
            return f"""
            <a
                class="label actionable"
                hx-get="/runs/{self.id}"
                hx-target="#container"
                hx-push-url="/_/runs/{self.id}"
            >
                {self.name}
            </a>
            """
        elif fmt == "heading":
            return f"""
            <h1
                hx-post="/runs/change/{self.id}"
                hx-swap="none"
                hx-trigger="input"
                hx-vals="js:name:event.target.innerHTML"
                class="editable"
                contenteditable
            >{self.name}</h1>
            """
        elif fmt == "targets":
            return f"""<div class="targets noprint">
                Targets: {"\n".join(
                    f'<span class="target target-{i}">{target:full}</span>'
                    for i, target in enumerate(self.targets)
                )}
                {self.new_target_input()}
            </div>
            """
        elif fmt == "detail":
            checked = self.get_checked()
            rows = [
                '<a class="noprint" href="/">↰ Runbooks</a><br>',
                f"{self:heading}",
                f"{self:targets}",
            ]
            for section in Runbook.from_id(self.runbook_id).sections:
                rows.append(f"<section><h2>{section.name}</h2><ul>")
                for item in section.items:
                    rows.append(item.as_checkbox(self, checked.get(item.id, {})))
                rows.append("</ul></section>")
            return "\n".join(rows)

    def rename(self, new_name):
        self.mutate(name=new_name)

    def get_checked(self):
        checked = {}
        with psycopg.connect(DB_SPEC) as conn:
            for target_id, item_id, type in conn.execute(
                """
                    SELECT target_id, item_id, type
                    FROM checkmarks
                    WHERE run_id=%(run_id)s
                """,
                {
                    "run_id": self.id,
                },
            ).fetchall():
                checked.setdefault(item_id, {})[target_id] = type
        return checked

    @property
    def targets(self):
        return Target.query(run_id=self.id)

    def new_target_input(self):
        return f"""<input
            type="text"
            name="name"
            placeholder="New target"
            hx-target="#container"
            hx-post="/targets/new/{self.id}"
            autofocus
        >
        """


class Target(Entity):
    def __format__(self, fmt):
        if fmt == "full":
            return self.name
