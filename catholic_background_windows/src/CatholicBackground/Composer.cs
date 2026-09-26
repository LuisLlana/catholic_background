// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later

using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;

namespace CatholicBackground;

/// <summary>
/// Composes a wallpaper for one monitor: the whole image, as big as possible without
/// cropping it, inside the area not covered by the taskbar, on top of a background that
/// covers the whole monitor (blurred image, average color or a chosen color).
/// </summary>
public static class Composer
{
    public static Bitmap Compose(Image image, Size screen, Rectangle free, string mode, Color color, out Color fill)
    {
        var canvas = new Bitmap(screen.Width, screen.Height, PixelFormat.Format24bppRgb);
        using var g = Graphics.FromImage(canvas);

        switch (mode)
        {
            case "color":
                fill = color;
                g.Clear(fill);
                break;
            case "average":
                fill = AverageColor(image);
                g.Clear(fill);
                break;
            default:
                fill = AverageColor(image);
                using (var blurred = Blurred(image, screen))
                    g.DrawImageUnscaled(blurred, 0, 0);
                break;
        }

        // Ignore absurd free areas
        if (free.Width < screen.Width / 2 || free.Height < screen.Height / 2)
            free = new Rectangle(Point.Empty, screen);

        // Largest size that keeps the proportions and fits entirely in the free area
        double scale = Math.Min((double)free.Width / image.Width, (double)free.Height / image.Height);
        int w = Math.Max(1, (int)Math.Round(image.Width * scale));
        int h = Math.Max(1, (int)Math.Round(image.Height * scale));
        var target = new Rectangle(free.X + (free.Width - w) / 2, free.Y + (free.Height - h) / 2, w, h);
        DrawScaled(g, image, target, new Rectangle(Point.Empty, image.Size), InterpolationMode.HighQualityBicubic);

        return canvas;
    }

    /// <summary>Draws without the dark borders GDI+ adds when scaling.</summary>
    private static void DrawScaled(Graphics g, Image image, Rectangle target, Rectangle source, InterpolationMode mode)
    {
        g.InterpolationMode = mode;
        g.PixelOffsetMode = PixelOffsetMode.HighQuality;
        g.CompositingQuality = CompositingQuality.HighQuality;
        using var attributes = new ImageAttributes();
        attributes.SetWrapMode(WrapMode.TileFlipXY);
        g.DrawImage(image, target, source.X, source.Y, source.Width, source.Height, GraphicsUnit.Pixel, attributes);
    }

    private static Bitmap Resize(Image image, int width, int height, Rectangle? source = null)
    {
        var result = new Bitmap(Math.Max(1, width), Math.Max(1, height), PixelFormat.Format24bppRgb);
        using var g = Graphics.FromImage(result);
        DrawScaled(g, image, new Rectangle(0, 0, result.Width, result.Height),
            source ?? new Rectangle(Point.Empty, image.Size), InterpolationMode.HighQualityBilinear);
        return result;
    }

    public static Color AverageColor(Image image)
    {
        using var small = Resize(image, 64, 64);
        long r = 0, g = 0, b = 0;
        ForEachPixel(small, (px, i) => { b += px[i]; g += px[i + 1]; r += px[i + 2]; });
        long n = 64 * 64;
        return Color.FromArgb((int)(r / n), (int)(g / n), (int)(b / n));
    }

    /// <summary>The image enlarged to cover the screen, blurred and slightly darkened.</summary>
    private static Bitmap Blurred(Image image, Size screen)
    {
        // Part of the image with the proportions of the screen
        int cw = image.Width, ch = (int)Math.Round((double)image.Width * screen.Height / screen.Width);
        if (ch > image.Height)
        {
            ch = image.Height;
            cw = (int)Math.Round((double)image.Height * screen.Width / screen.Height);
        }
        var crop = new Rectangle((image.Width - cw) / 2, (image.Height - ch) / 2, cw, ch);

        // Blur: shrink to a few pixels and enlarge again in smooth steps
        const int tinyWidth = 16;
        var current = Resize(image, tinyWidth, Math.Max(1, (int)Math.Round((double)tinyWidth * screen.Height / screen.Width)), crop);
        ForEachPixel(current, (px, i) =>
        {
            px[i] = (byte)(px[i] * 0.73);
            px[i + 1] = (byte)(px[i + 1] * 0.73);
            px[i + 2] = (byte)(px[i + 2] * 0.73);
        }, write: true);
        while (current.Width * 4 < screen.Width)
        {
            var next = Resize(current, current.Width * 2, current.Height * 2);
            current.Dispose();
            current = next;
        }
        var result = Resize(current, screen.Width, screen.Height);
        current.Dispose();
        return result;
    }

    private delegate void PixelAction(byte[] pixels, int index);

    /// <summary>Visits the BGR bytes of a 24 bpp bitmap.</summary>
    private static void ForEachPixel(Bitmap bitmap, PixelAction action, bool write = false)
    {
        var rect = new Rectangle(0, 0, bitmap.Width, bitmap.Height);
        var data = bitmap.LockBits(rect, write ? ImageLockMode.ReadWrite : ImageLockMode.ReadOnly, PixelFormat.Format24bppRgb);
        try
        {
            var bytes = new byte[data.Stride * data.Height];
            Marshal.Copy(data.Scan0, bytes, 0, bytes.Length);
            for (int y = 0; y < data.Height; y++)
                for (int x = 0; x < data.Width; x++)
                    action(bytes, y * data.Stride + x * 3);
            if (write)
                Marshal.Copy(bytes, 0, data.Scan0, bytes.Length);
        }
        finally
        {
            bitmap.UnlockBits(data);
        }
    }

    /// <summary>Loads an image applying its EXIF orientation.</summary>
    public static Bitmap Load(byte[] bytes)
    {
        using var stream = new MemoryStream(bytes);
        using var image = Image.FromStream(stream, useEmbeddedColorManagement: false, validateImageData: true);
        var bitmap = new Bitmap(image);
        const int OrientationTag = 0x0112;
        if (Array.IndexOf(image.PropertyIdList, OrientationTag) >= 0)
        {
            var rotate = image.GetPropertyItem(OrientationTag)?.Value?[0] switch
            {
                2 => RotateFlipType.RotateNoneFlipX,
                3 => RotateFlipType.Rotate180FlipNone,
                4 => RotateFlipType.Rotate180FlipX,
                5 => RotateFlipType.Rotate90FlipX,
                6 => RotateFlipType.Rotate90FlipNone,
                7 => RotateFlipType.Rotate270FlipX,
                8 => RotateFlipType.Rotate270FlipNone,
                _ => RotateFlipType.RotateNoneFlipNone,
            };
            bitmap.RotateFlip(rotate);
        }
        return bitmap;
    }

    public static void SaveJpeg(Bitmap bitmap, string path)
    {
        var codec = ImageCodecInfo.GetImageEncoders().First(c => c.FormatID == ImageFormat.Jpeg.Guid);
        using var parameters = new EncoderParameters(1);
        parameters.Param[0] = new EncoderParameter(Encoder.Quality, 92L);
        bitmap.Save(path, codec, parameters);
    }

    public static Color ParseColor(string hex)
    {
        try
        {
            return ColorTranslator.FromHtml(hex);
        }
        catch (Exception)
        {
            return Color.Black;
        }
    }

    public static string ToHex(Color color) => $"#{color.R:x2}{color.G:x2}{color.B:x2}";
}
