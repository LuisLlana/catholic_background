# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

# Image of the day on the login screen (SDDM, LightDM): a helper run as root with pkexec.
# The same login-background as catholic_background_gtk; its paths come from its folder name.
set(LOGIN_HELPER "${CMAKE_INSTALL_PREFIX}/libexec/catholic-background/login-background" PARENT_SCOPE)
set(LOGIN_HELPER "${CMAKE_INSTALL_PREFIX}/libexec/catholic-background/login-background")

install(PROGRAMS login-background DESTINATION ${CMAKE_INSTALL_PREFIX}/libexec/catholic-background)

configure_file(catholic-background-login.service.in ${CMAKE_CURRENT_BINARY_DIR}/catholic-background-login.service @ONLY)
configure_file(es.llana.catholicbackground.login.policy.in ${CMAKE_CURRENT_BINARY_DIR}/es.llana.catholicbackground.login.policy @ONLY)
install(FILES
    ${CMAKE_CURRENT_BINARY_DIR}/catholic-background-login.service
    catholic-background-login.timer
    DESTINATION ${CMAKE_INSTALL_PREFIX}/lib/systemd/system
)
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/es.llana.catholicbackground.login.policy
        DESTINATION ${KDE_INSTALL_DATADIR}/polkit-1/actions)
