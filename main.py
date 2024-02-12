import matplotlib.pyplot as plt
import sympy
from kempe_linkage import KempeLinkage
from matplotlib.animation import FuncAnimation
from options import Visibility

def main() -> None:
    linkage = KempeLinkage(radius = 4, pen_start = (2, 2.2), visible = Visibility.ALL)
    x, y = sympy.symbols("x y", real = True)
    linkage.from_curve(x - y + 0.2, x, y)
    pen_trace_xs, pen_trace_ys = [], []

    def animate(_) -> None:
        linkage.increase_alpha(1)
        result = linkage.solve()
        print(result, linkage.alpha_degrees)
        x, y = linkage.coords(linkage.pen)
        pen_trace_xs.append(x)
        pen_trace_ys.append(y)

        link_lines = []
        for link in linkage.visible_links:
            (x1, y1), (x2, y2) = linkage.all_coords(link.a, link.b)
            link_lines.extend([[x1, x2], [y1, y2]])

        plt.delaxes()
        plt.axis("equal")
        plt.plot(x, y, marker = "o")
        plt.plot(*link_lines)
        plt.plot(pen_trace_xs, pen_trace_ys)

    figure = plt.figure()
    _animation = FuncAnimation(figure, animate, interval = 10)
    plt.show()

if __name__ == "__main__":
    main()
