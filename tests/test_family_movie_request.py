from studio.services.family_movie_request import family_capture_request


def test_family_movie_frames():
    assert family_capture_request({"duration_seconds": 15})["frame_count"] == 90
