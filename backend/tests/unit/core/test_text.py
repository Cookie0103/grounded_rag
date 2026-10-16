from app.core.text import search_text


def test_search_text_puts_the_heading_path_before_the_text() -> None:
    assert search_text("环境变量 > 存储", "S3 的配置项") == "环境变量 > 存储\nS3 的配置项"
