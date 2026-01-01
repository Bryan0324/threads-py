from src.threads_py import ThreadsClient
token = ""  # Insert your access token here for testing
user_id = ""  # Insert your user ID here for testing
def test_client_instantiation():
    client = ThreadsClient(access_token=token, user_id=user_id)
    # post = client.create_carousel_post(text="貓咪", media_urls=[("IMAGE", "https://http.cat/404.jpg"), ("IMAGE", "https://http.cat/502.jpg"), ("IMAGE", "https://http.cat/100.jpg")])
    # post.publish().reply(
    #     client.create_post("測試功能")
    # )
    client.close()
