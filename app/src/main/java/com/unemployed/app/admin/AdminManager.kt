package com.unemployed.app.admin
object AdminManager {
    var masterKey: String = "f1d61f865d8f43aa27f9bee5b5e56d3c"
    fun isAuthorized(key: String): Boolean = key == masterKey
}
