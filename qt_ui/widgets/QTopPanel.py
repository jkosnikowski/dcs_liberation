from typing import Optional

from PySide2.QtWidgets import (
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
)

import qt_ui.uiconstants as CONST
from game import Game
from game.event import CAP, CAS, FrontlineAttackEvent
from qt_ui.models import GameModel
from qt_ui.widgets.QBudgetBox import QBudgetBox
from qt_ui.widgets.QFactionsInfos import QFactionsInfos
from qt_ui.widgets.QTurnCounter import QTurnCounter
from qt_ui.widgets.clientslots import MaxPlayerCount
from qt_ui.windows.GameUpdateSignal import GameUpdateSignal
from qt_ui.windows.QWaitingForMissionResultWindow import \
    QWaitingForMissionResultWindow
from qt_ui.windows.settings.QSettingsWindow import QSettingsWindow
from qt_ui.windows.stats.QStatsWindow import QStatsWindow


class QTopPanel(QFrame):

    def __init__(self, game_model: GameModel):
        super(QTopPanel, self).__init__()
        self.game_model = game_model
        self.setMaximumHeight(70)
        self.init_ui()
        GameUpdateSignal.get_instance().gameupdated.connect(self.setGame)
        GameUpdateSignal.get_instance().budgetupdated.connect(self.budget_update)

    @property
    def game(self) -> Optional[Game]:
        return self.game_model.game

    def init_ui(self):

        self.turnCounter = QTurnCounter()
        self.budgetBox = QBudgetBox(self.game)

        self.passTurnButton = QPushButton("Pass Turn")
        self.passTurnButton.setIcon(CONST.ICONS["PassTurn"])
        self.passTurnButton.setProperty("style", "btn-primary")
        self.passTurnButton.clicked.connect(self.passTurn)

        self.proceedButton = QPushButton("Take off")
        self.proceedButton.setIcon(CONST.ICONS["Proceed"])
        self.proceedButton.setProperty("style", "start-button")
        self.proceedButton.clicked.connect(self.launch_mission)
        if self.game and self.game.turn == 0:
            self.proceedButton.setEnabled(False)

        self.factionsInfos = QFactionsInfos(self.game)

        self.settings = QPushButton("Settings")
        self.settings.setIcon(CONST.ICONS["Settings"])
        self.settings.setProperty("style", "btn-primary")
        self.settings.clicked.connect(self.openSettings)

        self.statistics = QPushButton("Statistics")
        self.statistics.setIcon(CONST.ICONS["Statistics"])
        self.statistics.setProperty("style", "btn-primary")
        self.statistics.clicked.connect(self.openStatisticsWindow)

        self.buttonBox = QGroupBox("Misc")
        self.buttonBoxLayout = QHBoxLayout()
        self.buttonBoxLayout.addWidget(self.settings)
        self.buttonBoxLayout.addWidget(self.statistics)
        self.buttonBox.setLayout(self.buttonBoxLayout)

        self.proceedBox = QGroupBox("Proceed")
        self.proceedBoxLayout = QHBoxLayout()
        self.proceedBoxLayout.addLayout(
            MaxPlayerCount(self.game_model.ato_model))
        self.proceedBoxLayout.addWidget(self.passTurnButton)
        self.proceedBoxLayout.addWidget(self.proceedButton)
        self.proceedBox.setLayout(self.proceedBoxLayout)

        self.layout = QHBoxLayout()
        self.layout.addWidget(self.factionsInfos)
        self.layout.addWidget(self.turnCounter)
        self.layout.addWidget(self.budgetBox)
        self.layout.addWidget(self.buttonBox)
        self.layout.addStretch(1)
        self.layout.addWidget(self.proceedBox)

        self.layout.setContentsMargins(0,0,0,0)
        self.setLayout(self.layout)

    def setGame(self, game: Optional[Game]):
        if game is None:
            return

        self.turnCounter.setCurrentTurn(self.game.turn, self.game.current_day)
        self.budgetBox.setGame(self.game)
        self.factionsInfos.setGame(self.game)

        if self.game and self.game.turn == 0:
            self.proceedButton.setEnabled(False)
        else:
            self.proceedButton.setEnabled(True)

    def openSettings(self):
        self.subwindow = QSettingsWindow(self.game)
        self.subwindow.show()

    def openStatisticsWindow(self):
        self.subwindow = QStatsWindow(self.game)
        self.subwindow.show()

    def passTurn(self):
        self.game.pass_turn(no_action=True)
        GameUpdateSignal.get_instance().updateGame(self.game)
        self.proceedButton.setEnabled(True)

    def ato_has_clients(self) -> bool:
        for package in self.game.blue_ato.packages:
            for flight in package.flights:
                if flight.client_count > 0:
                    return True
        return False

    def confirm_no_client_launch(self) -> bool:
        result = QMessageBox.question(
            self,
            "Continue without client slots?",
            ("No client slots have been created for players. Continuing will "
             "allow the AI to perform the mission, but players will be unable "
             "to participate.<br />"
             "<br />"
             "To add client slots for players, select a package from the "
             "Packages panel on the left of the main window, and then a flight "
             "from the Flights panel below the Packages panel. The edit button "
             "below the Flights panel will allow you to edit the number of "
             "client slots in the flight. Each client slot allows one player."),
            QMessageBox.No,
            QMessageBox.Yes
        )
        return result == QMessageBox.Yes

    def launch_mission(self):
        """Finishes planning and waits for mission completion."""
        if not self.ato_has_clients() and not self.confirm_no_client_launch():
            return

        # TODO: Refactor this nonsense.
        game_event = None
        for event in self.game.events:
            if isinstance(event,
                          FrontlineAttackEvent) and event.is_player_attacking:
                game_event = event
        if game_event is None:
            game_event = FrontlineAttackEvent(
                self.game,
                self.game.theater.controlpoints[0],
                self.game.theater.controlpoints[0],
                self.game.theater.controlpoints[0].position,
                self.game.player_name,
                self.game.enemy_name)
        game_event.is_awacs_enabled = True
        game_event.ca_slots = 1
        game_event.departure_cp = self.game.theater.controlpoints[0]
        game_event.player_attacking({CAS: {}, CAP: {}})
        game_event.depart_from = self.game.theater.controlpoints[0]

        self.game.initiate_event(game_event)
        waiting = QWaitingForMissionResultWindow(game_event, self.game)
        waiting.show()

    def budget_update(self, game:Game):
        self.budgetBox.setGame(game)
