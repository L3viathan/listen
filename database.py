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

        elif fmt == "detail":
            return f"""
            <a class="noprint" href="/">↰ Runbooks</a><br>
            {self:heading}

            {"\n".join(f"{section:detail}" for section in self.sections)}

            {self.new_section_input(self.id)}

            <hr>
            {self:runs}
            """
        else:
            raise f"unknown format code {fmt}"


class Section(Entity):
    @property
    def items(self):
        return Item.query(section_id=self.id, order_by="rank ASC")

    def rename(self, new_name):
        self.mutate(name=new_name)

    @staticmethod
    def new_item_input(id):
        return f"""<input
            type="text"
            name="name"
            placeholder="New item"
            hx-swap="outerHTML"
            hx-post="/items/new/{id}"
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

    def as_checkbox(self, run, checked):
        if self.type == "once":
            return f"""
                <li
                    hx-post="/checkmarks/check/{run.id}/{self.id}"
                    hx-swap="outerHTML"
                    class="{"" if checked else "un"}checked actionable"
                >{self.name}</li>
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
                        class="{"" if target.id in checked else "un"}checked actionable"
                        hx-swap="outerHTML"
                        hx-target="closest li.multi"
                        hx-post="/checkmarks/check/{run.id}/{self.id}/{target.id}"
                    ><div class="multilabel target target-{i}">{target.name}</div></li>'''
                    for i, target in enumerate(run.targets)
                )}
                </ul>
                </li>
            """

    def toggle(self):
        new_type = "once" if self.type == "each" else "each"
        self.mutate(type=new_type)

    def check_for(self, run, target_id=None):
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
                        """
                            DELETE FROM checkmarks
                            WHERE run_id=%(run_id)s AND item_id=%(item_id)s
                        """,
                        {"run_id": run.id, "item_id": self.id},
                    )
                else:
                    conn.execute(
                        """
                            INSERT INTO checkmarks (run_id, item_id)
                            VALUES (%(run_id)s, %(item_id)s)
                        """,
                        {"run_id": run.id, "item_id": self.id},
                    )
            else:
                if target_id in checked_target_ids:
                    conn.execute(
                        """
                            DELETE FROM checkmarks
                            WHERE run_id=%(run_id)s
                                AND item_id=%(item_id)s
                                AND target_id=%(target_id)s
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
                            INSERT INTO checkmarks (run_id, item_id, target_id)
                            VALUES (%(run_id)s, %(item_id)s, %(target_id)s)
                        """,
                        {
                            "run_id": run.id,
                            "item_id": self.id,
                            "target_id": target_id,
                        },
                    )
            conn.commit()
            return self.as_checkbox(run, run.get_checked().get(self.id, []))

    def rename(self, new_name):
        self.mutate(name=new_name)


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
                    rows.append(item.as_checkbox(self, checked.get(item.id, [])))
                rows.append("</ul></section>")
            return "\n".join(rows)

    def rename(self, new_name):
        self.mutate(name=new_name)

    def get_checked(self):
        checked = {}
        with psycopg.connect(DB_SPEC) as conn:
            for target_id, item_id in conn.execute(
                """
                    SELECT target_id, item_id
                    FROM checkmarks
                    WHERE run_id=%(run_id)s
                """,
                {
                    "run_id": self.id,
                },
            ).fetchall():
                checked.setdefault(item_id, []).append(target_id)
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
        >
        """


class Target(Entity):
    def __format__(self, fmt):
        if fmt == "full":
            return self.name
