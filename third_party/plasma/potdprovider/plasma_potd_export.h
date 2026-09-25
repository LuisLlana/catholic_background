// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Minimal replacement for the plasma_potd_export.h generated when building
// kdeplasma-addons. Only used when the system does not install these headers
// (e.g. Debian 13).

#pragma once

#define PLASMA_POTD_EXPORT __attribute__((visibility("default")))
#define PLASMA_POTD_NO_EXPORT __attribute__((visibility("hidden")))
