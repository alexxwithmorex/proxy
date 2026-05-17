I used TCP (socket.SOCK_STREAM) since HTTP and HTTPS run on top of TCP as it is a reliable and ordered protocol, necessary for web traffic.\
I use the loopback address 127.0.0.1 to run the server locally, the port 8080 to listen to the requests from the browser, \
the default port 80 to handle HTTP requests and most of the time the port 443 for HTTPS requests (port number is assigned dynamically for https in case there’s an exception). \
\
For every request, two sockets are running simulatenously,\
socket A, created when the browser connects and socket B, opened by the proxy to the real server : \
Browser (client) ← socket A → proxy ← socket B → Original web server\


handle_http : \
I get the server’s response in chunks of 4096 bytes and then retransmit them to the browser, if one of them is empty, that means there’s no more data to send, the handling of that request is over, I close the sockets. \

handle_https : \
Since the first message was just a connection request, I now wait for the actual data to start being transmitted. \
I watch both sockets using select, which blocks until one of them has data ready to read (or 5 seconds pass with no data, I close the connection). \
Once select detects incoming data from one or both sockets (adds the socket to the readable list), I fetch the chunks of data (4096 bytes per chunk here as well) from that socket, then forward it to the other one.\
If it came from the browser I send it to the server, and if it came from the server I send it to the browser.

The blacklist : \
Each of the incoming requests gets their own thread, so multiple clients at a time can be handled. \
For the blacklist I used a lock so that only one thread could access it at the time, to avoid incoherencies. \
The blacklist management console is really simple, it just waits for an input, checks the command and executes it if recognized or shows an error message if not.\
It does that in a while loop and stops only if the program is interrupted since the thread is set as daemon (dies automatically when program stops). \
When a HTTPS page is blocked, the browser will show a connection failure and Unexpected End Of File error.\
Since HTTPS is encrypted and I just retransmit the bytes blindly, I cannot inject a custom message for errors, the only thing I can do is open and close the bridge, whereas for HTTP, as nothing is encrypted I can send whatever message I like in case of blacklisted domain name.
