// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later
package es.llana.catholicbackground.ui

import android.content.Context
import es.llana.catholicbackground.R
import es.llana.catholicbackground.data.Problem
import es.llana.catholicbackground.data.ServerException

/** Message of a server problem in the language of the device. */
fun problemText(context: Context, e: ServerException): String = when (e.problem) {
    Problem.INVALID_URL -> context.getString(R.string.problem_invalid_url)
    Problem.NO_IMAGE -> context.getString(R.string.problem_no_image)
    Problem.CONNECTION -> context.getString(R.string.problem_connection, e.message ?: "")
    Problem.HTTP -> context.getString(R.string.problem_http, e.message ?: "")
    Problem.INVALID_ANSWER -> context.getString(R.string.problem_invalid_answer)
}
