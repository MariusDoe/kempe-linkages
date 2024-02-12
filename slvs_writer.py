from type_aliases import Point, Line
from typing import Optional

def to_hex(value: int) -> str:
    return hex(value)[2:].rjust(8, "0")

class SlvsWriter:
    declarations: list[str]
    object_ids: dict[int, int]
    next_id = 1
    workplane_id: int

    def __init__(self) -> None:
        self.declarations = []
        self.object_ids = {}
        self.group_id = self.new_id()
        references_group_id = self.add_references_group()
        origin_id = self.add_origin()
        workplane_normal_id = self.add_workplane_normal(origin_id)
        self.add_workplane(origin_id, workplane_normal_id, references_group_id)
        self.add_workplane(origin_id, workplane_normal_id, references_group_id)
        self.workplane_id = self.add_workplane(origin_id, workplane_normal_id, references_group_id)
        self.add_group(self.group_id, origin_id)

    def write(self, path: str) -> None:
        declaration_order = ["Group", "Param", "Request", "Entity", "Constraint"]
        def declaration_key(declaration: str) -> int:
            type = declaration.split(".", maxsplit = 1)[0]
            return declaration_order.index(type)
        slvs = "\n".join(["\xb1\xb2\xb3SolveSpaceREVa\n", *sorted(self.declarations, key = declaration_key)])
        with open(path, "w") as file:
            file.write(slvs)

    def new_id(self, higher_order_id = 0) -> int:
        id = self.next_id
        self.next_id += 1
        return id | (higher_order_id << 16)

    def new_id_in_group(self) -> int:
        return self.new_id(self.group_id | 0x8000)

    def object_id(self, object) -> int:
        return self.object_ids[id(object)]

    def set_object_id(self, object, new_id: int) -> None:
        self.object_ids[id(object)] = new_id

    def declare(self, lines: str) -> None:
        declaration = ""
        lines = lines.split("\n")
        for line in lines:
            line = line.strip()
            if line == "":
                continue
            declaration += line + "\n"
        self.declarations.append(declaration)

    def add_origin(self) -> int:
        origin_id = self.new_id()
        self.declare(f"""
            Entity.h.v={to_hex(origin_id)}
            Entity.type=2000
            Entity.construction=0
            Entity.actVisible=1
            AddEntity
        """)
        for _ in range(3):
            self.add_param(0)
        return origin_id

    def add_workplane_normal(self, origin_id: int) -> int:
        normal_id = self.new_id_in_group()
        self.declare(f"""
            Entity.h.v={to_hex(normal_id)}
            Entity.type=3010
            Entity.construction=0
            Entity.point[0].v={to_hex(origin_id)}
            Entity.actNormal.w=1.00000000000000000000
            Entity.actVisible=1
            AddEntity
        """)
        for _ in range(4):
            self.add_param(0)
        return normal_id

    def add_workplane(self, origin_id: int, normal_id: int, group_id: int) -> int:
        workplane_id = self.new_id_in_group()
        self.declare(f"""
            Entity.h.v={to_hex(workplane_id)}
            Entity.type=10000
            Entity.construction=0
            Entity.point[0].v={to_hex(origin_id)}
            Entity.normal.v={to_hex(normal_id)}
            Entity.actVisible=1
            AddEntity
        """)
        self.add_request(100, workplane_id, group_id)
        return workplane_id

    def add_references_group(self) -> int:
        group_id = self.new_id()
        self.declare(f"""
            Group.h.v={to_hex(group_id)}
            Group.type=5000
            Group.name=#references
            Group.skipFirst=0
            Group.predef.swapUV=0
            Group.predef.negateU=0
            Group.predef.negateV=0
            Group.visible=1
            Group.suppress=0
            Group.relaxConstraints=0
            Group.remap={{
            }}
            Group.impFile=
            Group.impFileRel=
            AddGroup
        """)
        return group_id

    def add_group(self, group_id: int, origin_id: int) -> None:
        self.declare(f"""
            Group.h.v={to_hex(group_id)}
            Group.type=5001
            Group.order=1
            Group.name=draw-in-plane
            Group.activeWorkplane.v={to_hex(self.workplane_id)}
            Group.subtype=6000
            Group.skipFirst=0
            Group.predef.q.w=1.00000000000000000000
            Group.predef.origin.v={to_hex(origin_id)}
            Group.predef.swapUV=0
            Group.predef.negateU=0
            Group.predef.negateV=0
            Group.visible=1
            Group.suppress=0
            Group.relaxConstraints=0
            Group.remap={{
            }}
            Group.impFile=
            Group.impFileRel=
            AddGroup
        """)

    def add_param(self, value: float) -> int:
        param_id = self.new_id_in_group()
        self.declare(f"""
            Param.h.v.={to_hex(param_id)}
            Param.val={value}
            AddParam
        """)
        return param_id

    def add_point(self, point: Point, x: float, y: float) -> int:
        point_id = self.new_id_in_group()
        self.declare(f"""
            Entity.h.v={to_hex(point_id)}
            Entity.type=2001
            Entity.construction=0
            Entity.workplane.v={to_hex(self.workplane_id)}
            Entity.actPoint.x={x}
            Entity.actPoint.y={y}
            Entity.actVisible=1
            AddEntity
        """)
        self.add_param(x)
        self.add_param(y)
        self.set_object_id(point, point_id)
        return point_id

    def add_request(self, type: int, workplane_id: int, group_id: int) -> int:
        request_id = self.new_id()
        self.declare(f"""
            Request.h.v={to_hex(request_id)}
            Request.type={type}
            Request.workplane.v={to_hex(workplane_id)}
            Request.group.v={to_hex(group_id)}
            Request.construction=0
            AddRequest
        """)
        return request_id

    def add_line(self, line: Line, a: Point, b: Point) -> int:
        line_id = self.new_id_in_group()
        self.declare(f"""
            Entity.h.v={to_hex(line_id)}
            Entity.type=11000
            Entity.construction=1
            Entity.point[0].v={to_hex(self.object_id(a))}
            Entity.point[1].v={to_hex(self.object_id(b))}
            Entity.workplane.v={to_hex(self.workplane_id)}
            Entity.actVisible=1
            AddEntity
        """)
        self.add_request(200, self.workplane_id, self.group_id)
        self.set_object_id(line, line_id)
        return line_id

    def add_constraint(
        self, *, type: int,
        value: Optional[float] = None,
        points: list[Point] = [],
        lines: list[Line] = []
    ) -> int:
        constraint_id = self.new_id()
        declaration = f"""
            Constraint.h.v={to_hex(constraint_id)}
            Constraint.type={type}
            Constraint.group.v={to_hex(self.group_id)}
            Constraint.workplane.v={to_hex(self.workplane_id)}
        """
        if value:
            declaration += f"Constraint.valA={value}\n"
        for index, point in enumerate(points):
            declaration += f"Constraint.pt{chr(ord('A') + index)}.v={to_hex(self.object_id(point))}\n"
        for index, line in enumerate(lines):
            declaration += f"Constraint.entity{chr(ord('A') + index)}.v={to_hex(self.object_id(line))}\n"
        declaration += f"""
            Constraint.other=0
            Constraint.reference=0
            AddConstraint
        """
        self.declare(declaration)
        return constraint_id
