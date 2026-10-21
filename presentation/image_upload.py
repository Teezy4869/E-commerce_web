class ImageUpload:
    """
    Presentation Layer — ImageUpload

    Accepts an image path or direct embedding vector and delegates image
    representation to ImageService.
    """

    def __init__(self, image_service):
        self.image_service = image_service

    def upload(self, image_input):
        print(f"  [ImageUpload] Processing image: {image_input}")
        embedding = self.image_service.prepare_query(image_input)
        print(f"  [ImageUpload] Generated embedding: {embedding}")
        return embedding
