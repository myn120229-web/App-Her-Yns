package com.unemployed.app.data
import retrofit2.http.*
interface ApiService {
    @GET("jobs") suspend fun getJobs(@Header("Authorization") token: String): List<Job>
}
data class Job(val id: String, val title: String, val company: String)
