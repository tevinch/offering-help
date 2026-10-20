package example

import com.nabobery.sdkgen.runtime.SdkResponseResult
import com.nabobery.sdkgen.transport.javahttp.JavaHttpSdkTransport
import com.sun.net.httpserver.HttpServer
import example.catalog.Book
import example.catalog.CatalogClient
import example.catalog.books.BooksClient
import java.net.InetSocketAddress
import java.net.http.HttpClient
import java.util.concurrent.atomic.AtomicInteger
import java.util.concurrent.atomic.AtomicReference
import kotlinx.coroutines.runBlocking

fun main() = runBlocking {
    val requests = AtomicInteger()
    val received = AtomicReference<String>()
    val server = HttpServer.create(InetSocketAddress("127.0.0.1", 0), 0)
    server.createContext("/") { exchange ->
        requests.incrementAndGet()
        received.set("${exchange.requestMethod} ${exchange.requestURI}")
        val valid = exchange.requestMethod == "GET" && exchange.requestURI.toString() == "/books/7"
        val json = if (valid) """{"id":7,"title":"山海笔记"}""" else """{"error":"unexpected request"}"""
        val bytes = json.toByteArray(Charsets.UTF_8)
        exchange.responseHeaders.add("Content-Type", "application/json; charset=utf-8")
        exchange.sendResponseHeaders(if (valid) 200 else 404, bytes.size.toLong())
        exchange.responseBody.use { it.write(bytes) }
    }
    server.start()
    try {
        val http = HttpClient.newBuilder().followRedirects(HttpClient.Redirect.NEVER).build()
        val client = CatalogClient(
            transport = JavaHttpSdkTransport(http),
            baseUri = "http://127.0.0.1:${server.address.port}",
        )
        val response = client.books.getBookWithResponse(id = 7)
        check(requests.get() == 1)
        check(received.get() == "GET /books/7")
        check(response.statusCode == 200)
        check(response is SdkResponseResult.Matched)
        val success = response.value
        check(success is BooksClient.GetBookResponse.SuccessJson)
        val book: Book = success.json
        check(book.id == 7)
        check(book.title == "山海笔记")
        println("GET /books/7 -> ${response.statusCode}; id=${book.id}; title=${book.title}; requests=${requests.get()}")
    } finally {
        server.stop(0)
    }
}
