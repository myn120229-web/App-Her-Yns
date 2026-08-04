
package com.unemployed.app

import retrofit2.http.GET
import retrofit2.http.Header

interface UnemployedApi {
    @GET("/jobs")
    suspend fun getJobs(@Header("Authorization") apiKey: String): List<Job>
}
