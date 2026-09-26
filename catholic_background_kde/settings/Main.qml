// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later

import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Dialogs
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import CatholicBackground

Kirigami.ApplicationWindow {
    id: root

    title: "Catholic Background Settings"
    width: Kirigami.Units.gridUnit * 32
    height: Kirigami.Units.gridUnit * 34
    minimumWidth: Kirigami.Units.gridUnit * 22
    minimumHeight: Kirigami.Units.gridUnit * 24

    pageStack.initialPage: mainPage
    pageStack.globalToolBar.style: Kirigami.ApplicationHeaderStyle.ToolBar

    function showMessage(ok, text) {
        message.type = ok ? Kirigami.MessageType.Positive : Kirigami.MessageType.Error;
        message.text = text;
        message.visible = true;
    }

    Connections {
        target: Backend
        function onTestFinished(ok, text) { root.showMessage(ok, text) }
        function onRefreshFinished(ok, text) { root.showMessage(ok, text) }
    }

    ColorDialog {
        id: colorDialog
        title: "Background color"
        onAccepted: form.backgroundColor = selectedColor
    }

    Component {
        id: aboutPage
        Kirigami.AboutPage {
            aboutData: Backend.aboutData
        }
    }

    Kirigami.ScrollablePage {
        id: mainPage

        title: "Catholic background of the day"

        actions: [
            Kirigami.Action {
                text: "Refresh wallpaper"
                icon.name: "view-refresh"
                enabled: !Backend.busy
                onTriggered: Backend.refreshWallpaper()
            },
            Kirigami.Action {
                text: "Use as wallpaper"
                icon.name: "preferences-desktop-wallpaper"
                enabled: !Backend.busy
                displayHint: Kirigami.DisplayHint.AlwaysHide
                onTriggered: Backend.setAsWallpaper()
            },
            Kirigami.Action {
                text: "About"
                icon.name: "help-about"
                displayHint: Kirigami.DisplayHint.AlwaysHide
                onTriggered: root.pageStack.pushDialogLayer(aboutPage)
            }
        ]

        ColumnLayout {
            spacing: Kirigami.Units.largeSpacing

            // Installation problems that make the options have no effect
            Kirigami.InlineMessage {
                Layout.fillWidth: true
                type: Kirigami.MessageType.Warning
                text: Backend.problem
                visible: text.length > 0
                actions: [
                    Kirigami.Action {
                        text: "Restart Plasma"
                        icon.name: "view-refresh"
                        visible: Backend.canRestartPlasma
                        onTriggered: Backend.restartPlasma()
                    }
                ]
            }

            Kirigami.InlineMessage {
                id: message
                Layout.fillWidth: true
                showCloseButton: true
                visible: false
            }

            // Today's image, as cached by Plasma
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: width * 9 / 16
                color: Kirigami.Theme.alternateBackgroundColor
                radius: Kirigami.Units.cornerRadius
                clip: true

                Image {
                    id: preview
                    anchors.fill: parent
                    source: Backend.imageUrl
                    fillMode: Image.PreserveAspectFit
                    asynchronous: true
                    cache: false
                    sourceSize.width: width * Screen.devicePixelRatio
                }

                Kirigami.PlaceholderMessage {
                    anchors.centerIn: parent
                    width: parent.width - Kirigami.Units.gridUnit * 4
                    visible: preview.status !== Image.Ready && !Backend.busy
                    icon.name: "catholic-background"
                    text: "No image yet"
                    explanation: "Use it as wallpaper or refresh it to download today's image."
                }

                QQC2.BusyIndicator {
                    anchors.centerIn: parent
                    running: Backend.busy
                    visible: running
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 0
                visible: Backend.title.length > 0 || Backend.author.length > 0

                Kirigami.Heading {
                    Layout.fillWidth: true
                    level: 2
                    text: Backend.title
                    wrapMode: Text.Wrap
                }
                QQC2.Label {
                    Layout.fillWidth: true
                    text: Backend.author
                    opacity: 0.7
                    wrapMode: Text.Wrap
                }
            }

            QQC2.Label {
                Layout.fillWidth: true
                text: Backend.lastCheck
                font: Kirigami.Theme.smallFont
                opacity: 0.7
                wrapMode: Text.Wrap
            }

            Kirigami.Separator {
                Layout.fillWidth: true
            }

            Kirigami.FormLayout {
                id: form
                Layout.fillWidth: true

                // Pending values, applied with the Apply button
                property string background: Backend.background
                property color backgroundColor: Backend.backgroundColor
                property int checkInterval: Backend.checkInterval

                readonly property bool changed: urlField.text.trim() !== Backend.serverUrl
                    || background !== Backend.background
                    // Compare as "#rrggbb": the color dialog may return HSV colors
                    || (background === "color" && backgroundColor.toString() !== Backend.backgroundColor.toString())
                    || checkInterval !== Backend.checkInterval

                RowLayout {
                    Kirigami.FormData.label: "Server URL:"
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.smallSpacing

                    QQC2.TextField {
                        id: urlField
                        Layout.fillWidth: true
                        implicitWidth: Kirigami.Units.gridUnit * 16
                        text: Backend.serverUrl
                        placeholderText: Backend.defaultUrl
                        inputMethodHints: Qt.ImhUrlCharactersOnly | Qt.ImhNoAutoUppercase
                        onAccepted: applyButton.clicked()
                    }
                    QQC2.Button {
                        text: "Test"
                        icon.name: "network-connect"
                        enabled: !Backend.busy
                        onClicked: Backend.testConnection(urlField.text)
                    }
                }

                Kirigami.Separator {
                    Kirigami.FormData.isSection: true
                }

                QQC2.RadioButton {
                    Kirigami.FormData.label: "Around the image:"
                    text: "Blurred image"
                    checked: form.background === "blur"
                    onToggled: form.background = "blur"
                }
                QQC2.RadioButton {
                    text: "Average color of the image"
                    checked: form.background === "average"
                    onToggled: form.background = "average"
                }
                RowLayout {
                    spacing: Kirigami.Units.smallSpacing

                    QQC2.RadioButton {
                        text: "Color:"
                        checked: form.background === "color"
                        onToggled: form.background = "color"
                    }
                    QQC2.Button {
                        id: colorButton
                        enabled: form.background === "color"
                        implicitWidth: Kirigami.Units.gridUnit * 3
                        QQC2.ToolTip.text: "Choose color"
                        QQC2.ToolTip.visible: hovered
                        onClicked: {
                            colorDialog.selectedColor = form.backgroundColor;
                            colorDialog.open();
                        }
                        contentItem: Rectangle {
                            implicitHeight: Kirigami.Units.gridUnit
                            radius: Kirigami.Units.cornerRadius
                            color: form.backgroundColor
                            opacity: colorButton.enabled ? 1 : 0.4
                            border.color: Kirigami.ColorUtils.linearInterpolation(Kirigami.Theme.backgroundColor, Kirigami.Theme.textColor, 0.3)
                        }
                    }
                }

                Kirigami.Separator {
                    Kirigami.FormData.isSection: true
                }

                RowLayout {
                    Kirigami.FormData.label: "Check the server every:"
                    spacing: Kirigami.Units.smallSpacing

                    QQC2.SpinBox {
                        id: intervalSpin
                        from: 5
                        to: 24 * 60
                        stepSize: 5
                        editable: true
                        value: form.checkInterval
                        onValueModified: form.checkInterval = value
                    }
                    QQC2.Label {
                        text: "minutes"
                    }
                }

                Kirigami.Separator {
                    Kirigami.FormData.isSection: true
                }

                RowLayout {
                    spacing: Kirigami.Units.smallSpacing

                    QQC2.Button {
                        id: applyButton
                        text: "Apply"
                        icon.name: "dialog-ok-apply"
                        enabled: !Backend.busy && form.changed
                        onClicked: {
                            if (Backend.applySettings(urlField.text, form.background, form.backgroundColor, form.checkInterval)) {
                                urlField.text = Backend.serverUrl;
                            } else {
                                root.showMessage(false, "The URL is not valid. It must start with http:// or https://.");
                            }
                        }
                    }
                    QQC2.Button {
                        text: "Defaults"
                        icon.name: "edit-undo"
                        enabled: !Backend.busy
                        onClicked: {
                            urlField.text = Backend.defaultUrl;
                            form.background = "blur";
                            form.backgroundColor = "#000000";
                            form.checkInterval = Backend.defaultCheckInterval;
                        }
                    }
                }
            }
        }
    }
}
