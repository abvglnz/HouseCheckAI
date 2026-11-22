"""Доми — анимированный персонаж ИИ-помощника HouseCheck AI (рисуется QPainter)."""

from __future__ import annotations

import math
import random

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QCursor, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient
from PySide6.QtWidgets import QWidget

MASCOT_NAME = "Доми"


class Mascot(QWidget):
    """Домик с глазами: моргает, следит за курсором, «думает» и «говорит».

    mood: idle | think | talk | happy
    """

    clicked = Signal()

    def __init__(self, size: int = 120, parent=None, interactive: bool = False):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.mood = "idle"
        self.t = random.random() * 10
        self.blink = 0.0
        self._next_blink = 2.5
        self._talk_phase = 0.0
        self.interactive = interactive
        if interactive:
            self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)

    def set_mood(self, mood: str):
        self.mood = mood
        self.update()

    def mouseReleaseEvent(self, e):
        if self.interactive:
            self.clicked.emit()

    def _tick(self):
        if not self.isVisible():
            return
        dt = 0.033
        self.t += dt
        self._next_blink -= dt
        if self._next_blink <= 0:
            self.blink = 1.0
            self._next_blink = random.uniform(2.4, 5.0)
        if self.blink > 0:
            self.blink = max(0.0, self.blink - dt * 7)
        if self.mood == "talk":
            self._talk_phase += dt * 14
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        s = self.width() / 100.0
        p.scale(s, s)
        bob = math.sin(self.t * 2.2) * (2.6 if self.mood != "think" else 1.2)
        squash = 1 + math.sin(self.t * 4.4) * 0.012

        # тень на полу
        shadow_w = 34 - bob * 1.4
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(23, 35, 63, 40))
        p.drawEllipse(QPointF(50, 93), shadow_w, 4.2)

        p.translate(50, 52 + bob)
        p.scale(1 / squash, squash)
        p.translate(-50, -52)

        # аура «ИИ»
        if self.mood in ("think", "talk"):
            glow = QRadialGradient(QPointF(50, 50), 52)
            glow.setColorAt(0, QColor(242, 138, 60, 70))
            glow.setColorAt(1, QColor(242, 138, 60, 0))
            p.setBrush(glow)
            p.drawEllipse(QPointF(50, 50), 52, 52)

        # труба
        p.setBrush(QColor("#22305A"))
        p.drawRoundedRect(QRectF(66, 14, 9, 18), 3, 3)
        # дымок-сердечки
        for k in range(2):
            phase = (self.t * 0.6 + k * 0.5) % 1.0
            alpha = int(160 * (1 - phase))
            p.setBrush(QColor(255, 179, 122, alpha))
            p.drawEllipse(QPointF(71 + math.sin(phase * 6 + k) * 3, 12 - phase * 14), 3 + phase * 3, 3 + phase * 3)

        # корпус
        body = QRectF(20, 40, 60, 50)
        g = QLinearGradient(body.topLeft(), body.bottomRight())
        g.setColorAt(0, QColor("#FFB37A"))
        g.setColorAt(1, QColor("#F28A3C"))
        p.setBrush(g)
        p.drawRoundedRect(body, 14, 14)

        # крыша
        roof = QPainterPath()
        roof.moveTo(12, 46)
        roof.quadTo(10, 42, 14, 39)
        roof.lineTo(46, 15)
        roof.quadTo(50, 12, 54, 15)
        roof.lineTo(86, 39)
        roof.quadTo(90, 42, 88, 46)
        roof.quadTo(86, 49, 82, 48)
        roof.lineTo(18, 48)
        roof.quadTo(14, 49, 12, 46)
        rg = QLinearGradient(QPointF(50, 12), QPointF(50, 48))
        rg.setColorAt(0, QColor("#2B3A6B"))
        rg.setColorAt(1, QColor("#17233F"))
        p.setBrush(rg)
        p.drawPath(roof)

        # антенна-искра на крыше
        p.setPen(QPen(QColor("#17233F"), 2.2, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(50, 14), QPointF(50, 6))
        p.setPen(Qt.NoPen)
        pulse = 1 + 0.25 * math.sin(self.t * 5)
        p.setBrush(QColor("#B9F36B"))
        self._star(p, QPointF(50, 5), 4.2 * pulse)

        # окошко-щёчки и лицо
        p.setBrush(QColor(255, 255, 255, 60))
        p.drawRoundedRect(QRectF(26, 46, 48, 10), 5, 5)

        # направление взгляда
        look = QPointF(0, 0)
        if self.mood == "think":
            look = QPointF(2.2 * math.cos(self.t * 1.5), -2.4)
        else:
            try:
                cur = self.mapFromGlobal(QCursor.pos())
                dx = cur.x() / s - 50
                dy = cur.y() / s - 60
                d = max(1.0, math.hypot(dx, dy))
                k = min(1.0, d / 120)
                look = QPointF(dx / d * 2.6 * k, dy / d * 2.2 * k)
            except Exception:
                pass

        eye_y = 62
        for ex in (39, 61):
            if self.mood == "happy":
                p.setPen(QPen(QColor("#17233F"), 3, Qt.SolidLine, Qt.RoundCap))
                p.setBrush(Qt.NoBrush)
                path = QPainterPath()
                path.moveTo(ex - 5, eye_y + 1)
                path.quadTo(ex, eye_y - 6, ex + 5, eye_y + 1)
                p.drawPath(path)
                p.setPen(Qt.NoPen)
                continue
            openness = 1 - self.blink
            h = max(1.0, 8.5 * openness)
            p.setBrush(QColor("#FFFFFF"))
            p.drawEllipse(QPointF(ex, eye_y), 7, h)
            if openness > 0.25:
                p.setBrush(QColor("#17233F"))
                p.drawEllipse(QPointF(ex + look.x(), eye_y + look.y()), 4, 4.4 * openness)
                p.setBrush(QColor("#FFFFFF"))
                p.drawEllipse(QPointF(ex + look.x() + 1.5, eye_y + look.y() - 1.6), 1.3, 1.3)

        # щёки
        p.setBrush(QColor(255, 120, 120, 90))
        p.drawEllipse(QPointF(29, 72), 4.5, 3)
        p.drawEllipse(QPointF(71, 72), 4.5, 3)

        # рот
        p.setPen(Qt.NoPen)
        if self.mood == "talk":
            open_h = 2 + 3.5 * abs(math.sin(self._talk_phase))
            p.setBrush(QColor("#7A2E14"))
            p.drawRoundedRect(QRectF(45, 73, 10, open_h + 1), 4, 4)
        elif self.mood == "think":
            p.setPen(QPen(QColor("#7A2E14"), 2.4, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(QPointF(46, 76), QPointF(54, 75))
        else:
            p.setPen(QPen(QColor("#7A2E14"), 2.6, Qt.SolidLine, Qt.RoundCap))
            p.setBrush(Qt.NoBrush)
            m = QPainterPath()
            m.moveTo(44, 73.5)
            m.quadTo(50, 79.5 if self.mood == "happy" else 78, 56, 73.5)
            p.drawPath(m)

        # дверь-«галстук»
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(23, 35, 63, 50))
        p.drawRoundedRect(QRectF(45, 82, 10, 8), 3, 3)

        # искры размышления
        if self.mood == "think":
            for k in range(3):
                a = self.t * 2.4 + k * 2.1
                pt = QPointF(50 + math.cos(a) * 44, 46 + math.sin(a) * 26)
                p.setBrush(QColor(242, 138, 60, 200))
                self._star(p, pt, 3 + k * 0.6)

    @staticmethod
    def _star(p: QPainter, c: QPointF, r: float):
        path = QPainterPath()
        for i in range(8):
            ang = math.pi / 4 * i - math.pi / 2
            rr = r if i % 2 == 0 else r * 0.38
            pt = QPointF(c.x() + math.cos(ang) * rr, c.y() + math.sin(ang) * rr)
            path.moveTo(pt) if i == 0 else path.lineTo(pt)
        path.closeSubpath()
        p.drawPath(path)
