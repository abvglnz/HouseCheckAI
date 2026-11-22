"""Интерактивная стилизованная карта Астаны (QPainter): пины ЖК, зум, панорама, подсказки."""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from theme_tokens import T
from ui_kit import C, font, score_color

LAT0, LAT1 = 51.055, 51.200
LNG0, LNG1 = 71.350, 71.510
KX = math.cos(math.radians(51.13))

RIVER = [(51.168, 71.350), (51.160, 71.372), (51.150, 71.390), (51.138, 71.402), (51.128, 71.412), (51.122, 71.425),
         (51.126, 71.440), (51.138, 71.452), (51.152, 71.460), (51.158, 71.475), (51.150, 71.492), (51.138, 71.510)]
PARKS = [((51.1255, 71.4300), 0.0045, 0.010), ((51.1050, 71.4150), 0.004, 0.009), ((51.1430, 71.4430), 0.003, 0.007), ((51.1180, 71.4500), 0.0035, 0.008)]
ROADS = [
    [(51.080, 71.414), (51.110, 71.414), (51.135, 71.414), (51.165, 71.412), (51.195, 71.410)],  # Туран/Кунаева
    [(51.075, 71.440), (51.120, 71.432), (51.150, 71.430), (51.195, 71.428)],  # Мангилик Ел/Республики
    [(51.160, 71.355), (51.165, 71.420), (51.170, 71.505)],  # Абая/Богенбай
    [(51.100, 71.360), (51.100, 71.440), (51.095, 71.505)],  # Кабанбай батыра
    [(51.135, 71.360), (51.135, 71.505)],
]
LABELS = [("Есиль", 51.098, 71.390), ("Сарыарка", 51.185, 71.385), ("Байконур", 51.178, 71.445), ("Алматы", 51.150, 71.490), ("Нура", 51.067, 71.470)]


class AstanaMap(QWidget):
    pin_clicked = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.items: list[dict] = []
        self.scores: dict[int, int] = {}
        self.zoom = 1.0
        self.offset = QPointF(0, 0)
        self.hover_id: int | None = None
        self.selected_id: int | None = None
        self._drag = None
        self._t = 0.0
        self._grow: dict[int, float] = {}
        self.setMouseTracking(True)
        self.setMinimumSize(420, 360)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)

    def set_items(self, items: list[dict], scores: dict[int, int]):
        self.items = items
        self.scores = scores
        self.update()

    def select(self, dev_id: int | None):
        self.selected_id = dev_id
        self.update()

    def _tick(self):
        if not self.isVisible():
            return
        self._t += 0.033
        for it in self.items:
            target = 1.0 if it["id"] in (self.hover_id, self.selected_id) else 0.0
            cur = self._grow.get(it["id"], 0.0)
            self._grow[it["id"]] = cur + (target - cur) * 0.25
        self.update()

    # проекция
    def _base(self):
        w, h = self.width(), self.height()
        span_x = (LNG1 - LNG0) * KX
        span_y = LAT1 - LAT0
        scale = min(w / span_x, h / span_y) * 0.96 * self.zoom
        cx = w / 2 + self.offset.x()
        cy = h / 2 + self.offset.y()
        return scale, cx, cy

    def project(self, lat: float, lng: float) -> QPointF:
        scale, cx, cy = self._base()
        x = (lng - (LNG0 + LNG1) / 2) * KX * scale + cx
        y = ((LAT0 + LAT1) / 2 - lat) * scale + cy
        return QPointF(x, y)

    def _path(self, pts) -> QPainterPath:
        path = QPainterPath()
        projected = [self.project(a, b) for a, b in pts]
        path.moveTo(projected[0])
        for i in range(1, len(projected)):
            p0, p1 = projected[i - 1], projected[i]
            mid = (p0 + p1) / 2
            path.quadTo(p0, mid)
        path.lineTo(projected[-1])
        return path

    def wheelEvent(self, e):
        old = self.zoom
        self.zoom = max(0.8, min(4.0, self.zoom * (1.12 if e.angleDelta().y() > 0 else 1 / 1.12)))
        pos = e.position()
        center = QPointF(self.width() / 2, self.height() / 2) + self.offset
        self.offset += (center - pos) * (self.zoom / old - 1)
        self.update()

    def mousePressEvent(self, e):
        self._drag = (e.position(), QPointF(self.offset))
        self._moved = False

    def mouseMoveEvent(self, e):
        if self._drag and e.buttons() & Qt.LeftButton:
            delta = e.position() - self._drag[0]
            if abs(delta.x()) + abs(delta.y()) > 3:
                self._moved = True
                self.setCursor(Qt.ClosedHandCursor)
            self.offset = self._drag[1] + delta
            self.update()
            return
        hit = self._hit(e.position())
        if hit != self.hover_id:
            self.hover_id = hit
            self.setCursor(Qt.PointingHandCursor if hit else Qt.OpenHandCursor)

    def mouseReleaseEvent(self, e):
        moved = getattr(self, "_moved", False)
        self._drag = None
        self.setCursor(Qt.PointingHandCursor if self.hover_id else Qt.OpenHandCursor)
        if not moved:
            hit = self._hit(e.position())
            if hit:
                self.selected_id = hit
                self.pin_clicked.emit(hit)

    def leaveEvent(self, e):
        self.hover_id = None

    def _hit(self, pos: QPointF):
        best, best_d = None, 22.0
        for it in self.items:
            pt = self.project(it["lat"], it["lng"]) + QPointF(0, -16)
            d = math.hypot(pt.x() - pos.x(), pt.y() - pos.y())
            if d < best_d:
                best, best_d = it["id"], d
        return best

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(self.rect()), 22, 22)
        p.setClipPath(clip)
        p.fillRect(self.rect(), C("map_land"))
        # сетка кварталов
        p.setPen(QPen(C("grid"), 1))
        scale, _, _ = self._base()
        step = max(18.0, 0.006 * scale)
        o = self.project(LAT1, LNG0)
        x = o.x() % step
        while x < self.width():
            p.drawLine(QPointF(x, 0), QPointF(x, self.height())); x += step
        y = o.y() % step
        while y < self.height():
            p.drawLine(QPointF(0, y), QPointF(self.width(), y)); y += step
        # парки
        p.setPen(Qt.NoPen)
        p.setBrush(C("map_park"))
        for (lat, lng), dlat, dlng in PARKS:
            a = self.project(lat + dlat, lng - dlng)
            b = self.project(lat - dlat, lng + dlng)
            p.drawRoundedRect(QRectF(a, b), 14, 14)
        # дороги
        p.setBrush(Qt.NoBrush)
        for road in ROADS:
            p.setPen(QPen(C("border_strong"), 7 * min(self.zoom, 1.6), Qt.SolidLine, Qt.RoundCap))
            p.drawPath(self._path(road))
            p.setPen(QPen(C("map_road"), 4.5 * min(self.zoom, 1.6), Qt.SolidLine, Qt.RoundCap))
            p.drawPath(self._path(road))
        # река Есиль
        river = self._path(RIVER)
        p.setPen(QPen(C("map_water"), 16 * min(self.zoom, 1.8), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPath(river)
        p.setPen(QPen(QColor(255, 255, 255, 90), 2, Qt.DashLine, Qt.RoundCap))
        p.drawPath(river)
        # подписи районов
        p.setFont(font(12, 800))
        for text, lat, lng in LABELS:
            pt = self.project(lat, lng)
            p.setPen(C("text_soft"))
            p.drawText(QRectF(pt.x() - 80, pt.y() - 10, 160, 20), Qt.AlignCenter, text.upper())
        river_label = self.project(51.133, 71.398)
        p.setFont(font(11, 700)); p.setPen(QColor(T["map_water"]).darker(160))
        p.drawText(QRectF(river_label.x() - 60, river_label.y() - 26, 120, 18), Qt.AlignCenter, "р. Есиль")

        # пины
        ordered = sorted(self.items, key=lambda it: (it["id"] in (self.hover_id, self.selected_id), -it["lat"]))
        for it in ordered:
            self._pin(p, it)
        # подсказка
        target = self.hover_id or self.selected_id
        it = next((x for x in self.items if x["id"] == target), None)
        if it:
            self._tooltip(p, it)
        # легенда
        self._legend(p)

    def _pin(self, p: QPainter, it: dict):
        pt = self.project(it["lat"], it["lng"])
        g = self._grow.get(it["id"], 0.0)
        score = self.scores.get(it["id"], 0)
        col = QColor(score_color(score))
        r = 13 + 5 * g
        if it["id"] == self.selected_id:
            pulse = (self._t * 0.8) % 1.0
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(col.red(), col.green(), col.blue(), int(110 * (1 - pulse))))
            p.drawEllipse(pt, 8 + pulse * 26, (8 + pulse * 26) * 0.45)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 45))
        p.drawEllipse(pt + QPointF(0, 1), 7, 3)
        head = pt + QPointF(0, -r - 6)
        path = QPainterPath()
        path.moveTo(pt)
        path.cubicTo(pt + QPointF(-r * 0.4, -r * 0.6), head + QPointF(-r, r * 0.5), head + QPointF(-r, 0))
        path.arcTo(QRectF(head.x() - r, head.y() - r, 2 * r, 2 * r), 180, -180)
        path.cubicTo(head + QPointF(r, r * 0.5), pt + QPointF(r * 0.4, -r * 0.6), pt)
        p.setBrush(col)
        p.setPen(QPen(QColor("#FFFFFF"), 2.5))
        p.drawPath(path)
        p.setPen(QColor("#FFFFFF"))
        p.setFont(font(int(10 + 3 * g), 800))
        p.drawText(QRectF(head.x() - r, head.y() - r, 2 * r, 2 * r), Qt.AlignCenter, str(score) if score else "?")

    def _tooltip(self, p: QPainter, it: dict):
        pt = self.project(it["lat"], it["lng"])
        title = it["name"]
        sub = it.get("address") or it.get("district") or "Астана"
        f1, f2 = font(14, 700), font(11, 500)
        w = max(QFontMetrics(f1).horizontalAdvance(title), QFontMetrics(f2).horizontalAdvance(sub)) + 32
        h = 58
        x = min(max(8, pt.x() - w / 2), self.width() - w - 8)
        y = pt.y() - 48 - h
        if y < 8:
            y = pt.y() + 12
        r = QRectF(x, y, w, h)
        for i in range(1, 6):
            sp = QPainterPath(); sp.addRoundedRect(r.adjusted(-i * 0.5, i, i * 0.5, i), 16, 16)
            p.fillPath(sp, QColor(0, 0, 0, 9))
        bg = QPainterPath(); bg.addRoundedRect(r, 16, 16)
        p.fillPath(bg, C("nav"))
        p.setPen(QColor("#FFFFFF")); p.setFont(f1)
        p.drawText(r.adjusted(16, 10, -10, -28), Qt.AlignLeft | Qt.AlignVCenter, title)
        p.setPen(C("nav_muted")); p.setFont(f2)
        p.drawText(r.adjusted(16, 30, -10, -8), Qt.AlignLeft | Qt.AlignVCenter, sub)

    def _legend(self, p: QPainter):
        entries = [("80+", T["positive"]), ("65+", T["accent"]), ("50+", T["warning"]), ("<50", T["danger"])]
        r = QRectF(16, self.height() - 46, 236, 30)
        bg = QPainterPath(); bg.addRoundedRect(r, 15, 15)
        p.fillPath(bg, C("surface", 235))
        p.setFont(font(11, 700))
        x = r.left() + 14
        for text, col in entries:
            p.setPen(Qt.NoPen); p.setBrush(QColor(col)); p.drawEllipse(QPointF(x + 5, r.center().y()), 5, 5)
            p.setPen(C("text_muted")); p.drawText(QRectF(x + 14, r.top(), 40, r.height()), Qt.AlignVCenter, text)
            x += 55
