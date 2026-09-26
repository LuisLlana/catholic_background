// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later

using System.Drawing;

namespace CatholicBackground;

public static class AppIcon
{
    public static Icon Load(Size? size = null)
    {
        using var stream = typeof(AppIcon).Assembly.GetManifestResourceStream("CatholicBackground.ico")!;
        return size is null ? new Icon(stream) : new Icon(stream, size.Value);
    }
}
