from tools.verify_release import check_source_completeness, check_tracks


def test_release_verifier_track_and_source_checks():
    source = check_source_completeness()
    tracks = check_tracks()
    assert source["python_files_scanned"] >= 10
    assert set(tracks) == {"easy", "medium", "hard"}
    assert all(info["points"] >= 100 for info in tracks.values())
