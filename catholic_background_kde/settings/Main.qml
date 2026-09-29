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
    width: Kirigami.Units.gridUnit * 62
    height: Kirigami.Units.gridUnit * 42
    minimumWidth: Kirigami.Units.gridUnit * 26
    minimumHeight: Kirigami.Units.gridUnit * 26

    pageStack.initialPage: dayPage
    pageStack.globalToolBar.style: Kirigami.ApplicationHeaderStyle.ToolBar

    Connections {
        target: Backend
        function onTestFinished(ok, text) { root.showPassiveNotification(text, ok ? "short" : "long") }
        function onRefreshFinished(ok, text) { root.showPassiveNotification(text, ok ? "short" : "long") }
    }

    Component {
        id: aboutPage
        Kirigami.AboutPage {
            aboutData: Backend.aboutData
        }
    }

    // ------------------------------------------------------------------ day viewer
    Kirigami.ScrollablePage {
        id: dayPage

        title: "Catholic background of the day"

        actions: [
            Kirigami.Action {
                text: "Refresh wallpaper"
                icon.name: "view-refresh"
                enabled: !Backend.busy
                onTriggered: Backend.refreshWallpaper()
            },
            Kirigami.Action {
                text: "Settings"
                icon.name: "configure"
                onTriggered: root.pageStack.pushDialogLayer(settingsPage, {}, {
                    "width": Kirigami.Units.gridUnit * 40, "height": Kirigami.Units.gridUnit * 30 })
            },
            Kirigami.Action {
                text: "Use Catholic background on every desktop"
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

            // ---- choice of the day
            RowLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing

                QQC2.ToolButton {
                    icon.name: "go-previous"
                    text: "Previous day"
                    display: QQC2.AbstractButton.IconOnly
                    QQC2.ToolTip.text: text
                    QQC2.ToolTip.visible: hovered
                    onClicked: Backend.shiftDay(-1)
                }
                QQC2.Button {
                    icon.name: "view-calendar-day"
                    text: Backend.viewDateText
                    QQC2.ToolTip.text: "Choose a day"
                    QQC2.ToolTip.visible: hovered
                    onClicked: calendar.openAt(Backend.viewYear, Backend.viewMonth)
                }
                QQC2.ToolButton {
                    icon.name: "go-next"
                    text: "Next day"
                    display: QQC2.AbstractButton.IconOnly
                    QQC2.ToolTip.text: text
                    QQC2.ToolTip.visible: hovered
                    onClicked: Backend.shiftDay(1)
                }
                QQC2.Button {
                    text: "Today"
                    icon.name: "go-jump-today"
                    enabled: !Backend.viewIsToday
                    onClicked: Backend.goToToday()
                }

                Item { Layout.fillWidth: true }

                QQC2.Button {
                    text: Backend.viewIsWallpaper ? "This is your wallpaper" : "Use as wallpaper"
                    icon.name: Backend.viewIsWallpaper ? "checkmark" : "preferences-desktop-wallpaper"
                    enabled: !Backend.viewIsWallpaper && !Backend.busy && !Backend.dayLoading && Backend.dayError.length === 0
                    onClicked: Backend.useViewedDayAsWallpaper()
                }
                QQC2.Button {
                    text: "Edit this image"
                    icon.name: "document-edit"
                    visible: (Backend.dayInfo.edit_url || "").length > 0 && !Backend.dayLoading
                    QQC2.ToolTip.text: "Opens the page of the artwork in the content manager"
                    QQC2.ToolTip.visible: hovered
                    onClicked: Qt.openUrlExternally(Backend.dayInfo.edit_url)
                }
            }

            QQC2.Label {
                Layout.fillWidth: true
                visible: Backend.wallpaperDateText.length > 0
                text: "The wallpaper shows the image of " + Backend.wallpaperDateText
                      + " until the next automatic check, which returns to today."
                wrapMode: Text.Wrap
                opacity: 0.8
            }

            // ---- the image and its data
            GridLayout {
                id: content
                Layout.fillWidth: true
                columns: width > Kirigami.Units.gridUnit * 42 ? 2 : 1
                columnSpacing: Kirigami.Units.largeSpacing * 2
                rowSpacing: Kirigami.Units.largeSpacing

                Rectangle {
                    // Proportions of the artwork (4:3 until it is loaded)
                    readonly property real ratio: dayImage.implicitWidth > 0 ? dayImage.implicitHeight / dayImage.implicitWidth : 0.75
                    // As big as the window allows, below the header and the bar of the day
                    readonly property real maxHeight: content.columns === 2
                        ? dayPage.height - Kirigami.Units.gridUnit * 8 : root.height * 0.7

                    Layout.fillWidth: true
                    Layout.preferredWidth: content.columns === 2 ? content.width * 0.66 : content.width
                    Layout.preferredHeight: Math.max(Kirigami.Units.gridUnit * 12, Math.min(maxHeight, width * ratio))
                    Layout.alignment: Qt.AlignTop
                    color: Kirigami.Theme.alternateBackgroundColor
                    radius: Kirigami.Units.cornerRadius
                    clip: true

                    Image {
                        id: dayImage
                        anchors.fill: parent
                        anchors.margins: Kirigami.Units.smallSpacing
                        source: Backend.dayImage
                        fillMode: Image.PreserveAspectFit
                        asynchronous: true
                        cache: false
                        visible: Backend.dayError.length === 0
                    }
                    QQC2.BusyIndicator {
                        anchors.centerIn: parent
                        running: Backend.dayLoading
                        visible: running
                    }
                    Kirigami.PlaceholderMessage {
                        anchors.centerIn: parent
                        width: parent.width - Kirigami.Units.gridUnit * 4
                        visible: Backend.dayError.length > 0 && !Backend.dayLoading
                        icon.name: "catholic-background"
                        text: Backend.dayError
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.preferredWidth: content.columns === 2 ? content.width * 0.34 : content.width
                    Layout.alignment: Qt.AlignTop
                    spacing: Kirigami.Units.smallSpacing
                    visible: Backend.dayError.length === 0 && !Backend.dayLoading

                    QQC2.Label {
                        Layout.fillWidth: true
                        visible: text.length > 0
                        text: Backend.dayInfo.reason || ""
                        color: "#c8962a"
                        font.bold: true
                        wrapMode: Text.Wrap
                    }
                    Kirigami.Heading {
                        Layout.fillWidth: true
                        level: 1
                        text: Backend.dayInfo.title || "Untitled"
                        wrapMode: Text.Wrap
                    }
                    QQC2.Label {
                        Layout.fillWidth: true
                        visible: text.length > 0
                        text: [Backend.dayInfo.author || "", Backend.dayInfo.date || ""].filter(t => t.length > 0).join(", ")
                        font.pointSize: Kirigami.Theme.defaultFont.pointSize * 1.15
                        wrapMode: Text.Wrap
                    }
                    QQC2.Label {
                        Layout.fillWidth: true
                        Layout.topMargin: Kirigami.Units.largeSpacing
                        visible: text.length > 0
                        text: Backend.dayInfo.description || ""
                        wrapMode: Text.Wrap
                    }

                    // Additional data, license and source, in this order
                    GridLayout {
                        Layout.fillWidth: true
                        Layout.topMargin: Kirigami.Units.largeSpacing
                        columns: 2
                        columnSpacing: Kirigami.Units.largeSpacing
                        rowSpacing: Kirigami.Units.smallSpacing

                        Repeater {
                            model: {
                                let rows = (Backend.dayInfo.extra || []).map(e => ({ "name": e.name, "value": e.value, "link": "" }))
                                if (Backend.dayInfo.license)
                                    rows.push({ "name": "License", "value": Backend.dayInfo.license, "link": "" })
                                if (Backend.dayInfo.source)
                                    rows.push({ "name": "Source", "value": Backend.dayInfo.source, "link": Backend.dayInfo.source })
                                // Two cells per row: name and value
                                let cells = []
                                for (let r of rows) {
                                    cells.push({ "text": r.name, "isName": true, "link": "" })
                                    cells.push({ "text": r.value, "isName": false, "link": r.link })
                                }
                                return cells
                            }
                            delegate: QQC2.Label {
                                required property var modelData
                                Layout.fillWidth: !modelData.isName
                                Layout.alignment: Qt.AlignTop
                                text: modelData.link ? "<a href=\"" + modelData.link + "\">" + modelData.text + "</a>" : modelData.text
                                textFormat: modelData.link ? Text.StyledText : Text.PlainText
                                font.bold: modelData.isName
                                opacity: modelData.isName ? 0.8 : 1
                                wrapMode: modelData.link ? Text.WrapAnywhere : Text.Wrap
                                onLinkActivated: link => Qt.openUrlExternally(link)
                                HoverHandler {
                                    enabled: modelData.link.length > 0
                                    cursorShape: Qt.PointingHandCursor
                                }
                            }
                        }
                    }
                }
            }

            QQC2.Label {
                Layout.fillWidth: true
                text: Backend.lastCheck
                font: Kirigami.Theme.smallFont
                opacity: 0.7
                wrapMode: Text.Wrap
            }
        }
    }

    // ------------------------------------------------------------------ calendar
    QQC2.Popup {
        id: calendar

        property int year: 2026
        property int month: 0   // 0–11, as MonthGrid

        function openAt(year, month) {
            calendar.year = year
            calendar.month = month - 1
            open()
        }
        function move(months) {
            let m = month + months
            year += Math.floor(m / 12)
            month = ((m % 12) + 12) % 12
        }

        parent: QQC2.Overlay.overlay
        anchors.centerIn: parent
        modal: true
        padding: Kirigami.Units.largeSpacing

        contentItem: ColumnLayout {
            spacing: Kirigami.Units.smallSpacing

            RowLayout {
                Layout.fillWidth: true
                QQC2.ToolButton { icon.name: "go-previous"; onClicked: calendar.move(-12); QQC2.ToolTip.text: "Previous year"; QQC2.ToolTip.visible: hovered; text: "«"; display: QQC2.AbstractButton.TextOnly }
                QQC2.ToolButton { icon.name: "go-previous"; onClicked: calendar.move(-1); QQC2.ToolTip.text: "Previous month"; QQC2.ToolTip.visible: hovered }
                Kirigami.Heading {
                    Layout.fillWidth: true
                    level: 3
                    horizontalAlignment: Text.AlignHCenter
                    text: Qt.locale().standaloneMonthName(calendar.month) + " " + calendar.year
                }
                QQC2.ToolButton { icon.name: "go-next"; onClicked: calendar.move(1); QQC2.ToolTip.text: "Next month"; QQC2.ToolTip.visible: hovered }
                QQC2.ToolButton { onClicked: calendar.move(12); QQC2.ToolTip.text: "Next year"; QQC2.ToolTip.visible: hovered; text: "»" }
            }
            QQC2.DayOfWeekRow {
                Layout.fillWidth: true
                locale: Qt.locale()
            }
            QQC2.MonthGrid {
                id: grid
                Layout.fillWidth: true
                Layout.preferredWidth: Kirigami.Units.gridUnit * 18
                month: calendar.month
                year: calendar.year
                locale: Qt.locale()
                delegate: QQC2.ToolButton {
                    required property var model
                    text: model.day
                    Kirigami.MnemonicData.enabled: false
                    opacity: model.month === grid.month ? 1 : 0.4
                    checkable: false
                    highlighted: model.year === Backend.viewYear && model.month === Backend.viewMonth - 1 && model.day === Backend.viewDay
                    font.bold: model.today
                    onClicked: {
                        Backend.loadDate(model.year, model.month + 1, model.day)
                        calendar.close()
                    }
                }
            }
            QQC2.Button {
                Layout.alignment: Qt.AlignHCenter
                text: "Today"
                icon.name: "go-jump-today"
                onClicked: {
                    Backend.goToToday()
                    calendar.close()
                }
            }
        }
    }

    // ------------------------------------------------------------------ settings
    ColorDialog {
        id: colorDialog
        title: "Background color"
        onAccepted: settingsForm.backgroundColor = selectedColor
    }

    Component {
        id: settingsPage

        Kirigami.ScrollablePage {
            title: "Settings"

            Kirigami.FormLayout {
                id: form

                // Pending values, applied with the Apply button
                property string background: Backend.background
                property color backgroundColor: Backend.backgroundColor
                property int checkInterval: Backend.checkInterval
                property string language: Backend.language
                property bool showLabel: Backend.showLabel

                readonly property bool changed: urlField.text.trim() !== Backend.serverUrl
                    || background !== Backend.background
                    // Compare as "#rrggbb": the color dialog may return HSV colors
                    || (background === "color" && backgroundColor.toString() !== Backend.backgroundColor.toString())
                    || checkInterval !== Backend.checkInterval
                    || language !== Backend.language
                    || showLabel !== Backend.showLabel

                Component.onCompleted: settingsForm = form

                RowLayout {
                    Kirigami.FormData.label: "Server URL:"
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.smallSpacing

                    QQC2.TextField {
                        id: urlField
                        Layout.fillWidth: true
                        implicitWidth: Kirigami.Units.gridUnit * 20
                        text: Backend.serverUrl
                        placeholderText: Backend.defaultUrl
                        inputMethodHints: Qt.ImhUrlCharactersOnly | Qt.ImhNoAutoUppercase
                    }
                    QQC2.Button {
                        text: "Test"
                        icon.name: "network-connect"
                        enabled: !Backend.busy
                        onClicked: Backend.testConnection(urlField.text)
                    }
                }

                QQC2.ComboBox {
                    id: languageBox
                    Kirigami.FormData.label: "Language of the texts:"
                    textRole: "name"
                    valueRole: "code"
                    model: [{ "code": "", "name": "System language (" + Backend.systemLanguageName + ")" }].concat(Backend.languages)
                    Component.onCompleted: currentIndex = Math.max(0, indexOfValue(form.language))
                    onModelChanged: currentIndex = Math.max(0, indexOfValue(form.language))
                    onActivated: form.language = currentValue
                }

                QQC2.CheckBox {
                    Kirigami.FormData.label: "Label:"
                    text: "Show the reason, title and author below the artwork"
                    checked: form.showLabel
                    onToggled: form.showLabel = checked
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
                            colorDialog.selectedColor = form.backgroundColor
                            colorDialog.open()
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
                        text: "Apply"
                        icon.name: "dialog-ok-apply"
                        enabled: !Backend.busy && form.changed
                        onClicked: {
                            if (Backend.applySettings(urlField.text, form.background, form.backgroundColor, form.checkInterval,
                                                      form.language, form.showLabel)) {
                                urlField.text = Backend.serverUrl
                            } else {
                                root.showPassiveNotification("The URL is not valid. It must start with http:// or https://.", "long")
                            }
                        }
                    }
                    QQC2.Button {
                        text: "Defaults"
                        icon.name: "edit-undo"
                        enabled: !Backend.busy
                        onClicked: {
                            urlField.text = Backend.defaultUrl
                            form.background = "blur"
                            form.backgroundColor = "#000000"
                            form.checkInterval = Backend.defaultCheckInterval
                            form.language = ""
                            form.showLabel = true
                            languageBox.currentIndex = 0
                        }
                    }
                }
            }
        }
    }

    // The form of the settings page (for the color dialog, which lives outside the page)
    property var settingsForm: null
}
