// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later

using System.Drawing;
using System.Security.Cryptography;
using System.Text.Json;

namespace CatholicBackground;

public sealed record DownloadedImage(byte[] Bytes, string Hash, string Title, string Author, Size Size);

/// <summary>
/// Access to the Catholic background of the day server.
/// Protocol: GET &lt;url&gt;?ts=&lt;Unix timestamp of today's local midnight&gt;
///   -> {"image": "&lt;base64&gt;", "title": ..., "author": ..., "date": ...}
/// </summary>
public static class ServerClient
{
    private static readonly HttpClient Http = new() { Timeout = TimeSpan.FromSeconds(60) };

    /// <summary>Base URL with ts=&lt;timestamp&gt;, keeping any other query parameters.</summary>
    public static Uri UrlForToday(string baseUrl)
    {
        if (!Uri.TryCreate(baseUrl.Trim(), UriKind.Absolute, out var uri) ||
            (uri.Scheme != Uri.UriSchemeHttp && uri.Scheme != Uri.UriSchemeHttps))
            throw new ServerException("The URL must start with http:// or https://.");

        long ts = new DateTimeOffset(DateTime.Today).ToUnixTimeSeconds();
        var parameters = uri.Query.TrimStart('?')
            .Split('&', StringSplitOptions.RemoveEmptyEntries)
            .Where(p => p.Split('=')[0] != "ts")
            .Append($"ts={ts}");
        return new UriBuilder(uri) { Query = string.Join("&", parameters) }.Uri;
    }

    public static string FormatTitle(string title, string date)
    {
        title = title.Trim();
        date = date.Trim();
        if (title.Length > 0 && date.Length > 0)
            return $"{title} ({date})";
        return title.Length > 0 ? title : date;
    }

    public static async Task<DownloadedImage> FetchAsync(string baseUrl, CancellationToken cancellationToken = default)
    {
        var url = UrlForToday(baseUrl);

        string body;
        try
        {
            using var response = await Http.GetAsync(url, cancellationToken);
            if (!response.IsSuccessStatusCode)
                throw new ServerException($"The server answered with HTTP {(int)response.StatusCode} {response.ReasonPhrase}.");
            body = await response.Content.ReadAsStringAsync(cancellationToken);
        }
        catch (HttpRequestException e)
        {
            throw new ServerException($"Could not connect to the server: {e.Message}");
        }
        catch (TaskCanceledException) when (!cancellationToken.IsCancellationRequested)
        {
            throw new ServerException("The server did not answer in time.");
        }

        JsonElement root;
        try
        {
            root = JsonDocument.Parse(body).RootElement;
        }
        catch (JsonException)
        {
            throw new ServerException("The server did not answer with JSON.");
        }
        if (root.ValueKind != JsonValueKind.Object ||
            !root.TryGetProperty("image", out var imageElement) || imageElement.ValueKind != JsonValueKind.String)
            throw new ServerException("The answer of the server has no \"image\" field.");

        var base64 = imageElement.GetString()!;
        if (base64.StartsWith("data:", StringComparison.Ordinal))
            base64 = base64[(base64.IndexOf(',') + 1)..];
        byte[] bytes;
        try
        {
            bytes = Convert.FromBase64String(base64);
        }
        catch (FormatException)
        {
            throw new ServerException("The \"image\" field is not valid base64.");
        }

        Size size;
        try
        {
            using var stream = new MemoryStream(bytes);
            using var image = Image.FromStream(stream, useEmbeddedColorManagement: false, validateImageData: true);
            size = image.Size;
        }
        catch (ArgumentException)
        {
            throw new ServerException("The \"image\" field does not contain an image that Windows can read (use JPEG or PNG).");
        }

        return new DownloadedImage(
            bytes,
            Convert.ToHexString(SHA1.HashData(bytes)).ToLowerInvariant(),
            FormatTitle(GetText(root, "title"), GetText(root, "date")),
            GetText(root, "author").Trim(),
            size);
    }

    private static string GetText(JsonElement root, string name) =>
        root.TryGetProperty(name, out var value)
            ? value.ValueKind switch
            {
                JsonValueKind.String => value.GetString() ?? "",
                JsonValueKind.Number => value.GetRawText(),
                _ => "",
            }
            : "";
}

public sealed class ServerException(string message) : Exception(message);
