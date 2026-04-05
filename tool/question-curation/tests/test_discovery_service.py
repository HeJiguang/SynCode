from app.services.discovery_service import CodeforcesLead, DiscoveryService


def test_discovery_service_filters_codeforces_results_by_keyword() -> None:
    payload = {
        "status": "OK",
        "result": {
            "problems": [
                {"contestId": 1, "index": "A", "name": "Two Sum", "rating": 800, "tags": ["implementation", "hashing"]},
                {"contestId": 2, "index": "B", "name": "Tree Diameter", "rating": 1600, "tags": ["trees", "dfs"]},
            ]
        },
    }
    service = DiscoveryService()

    leads = service._parse_codeforces_payload(payload, keyword="sum")

    assert leads == [
        CodeforcesLead(
            title="Two Sum",
            source_platform="codeforces",
            source_url="https://codeforces.com/problemset/problem/1/A",
            source_problem_id="1A",
            difficulty=1,
            tags=["implementation", "hashing"],
        )
    ]


def test_discovery_service_builds_candidate_seed_from_reference_url() -> None:
    service = DiscoveryService()

    seed = service.seed_from_reference_url(
        title="Two Sum",
        source_platform="leetcode",
        url="https://leetcode.com/problems/two-sum/",
    )

    assert seed["title"] == "Two Sum"
    assert seed["source_type"] == "reference_url"
    assert seed["source_platform"] == "leetcode"
    assert seed["source_url"] == "https://leetcode.com/problems/two-sum/"


def test_discovery_service_extracts_plain_text_from_html() -> None:
    service = DiscoveryService()

    extracted = service.extract_reference_text(
        """
        <html>
          <head><title>Two Sum</title></head>
          <body>
            <article>
              <h1>Two Sum</h1>
              <p>Given an array of integers and a target.</p>
              <pre>Sample Input\n4\n2 7 11 15\n9</pre>
              <pre>Sample Output\n0 1</pre>
            </article>
          </body>
        </html>
        """
    )

    assert "Two Sum" in extracted
    assert "Given an array of integers and a target." in extracted
    assert "Sample Input" in extracted


def test_discovery_service_extracts_leetcode_description_block() -> None:
    service = DiscoveryService()

    extracted = service.extract_reference_text(
        """
        <html>
          <body>
            <div data-track-load="description_content">
              <p>Given an integer array nums and an integer target.</p>
              <p>Return indices of the two numbers.</p>
            </div>
          </body>
        </html>
        """,
        url="https://leetcode.com/problems/two-sum/",
    )

    assert "Given an integer array nums and an integer target." in extracted
    assert "Return indices of the two numbers." in extracted


def test_discovery_service_extracts_luogu_main_content_block() -> None:
    service = DiscoveryService()

    extracted = service.extract_reference_text(
        """
        <html>
          <body>
            <article class="main">
              <h1>P1001 A+B Problem</h1>
              <section>
                <p>输入两个整数，输出它们的和。</p>
              </section>
            </article>
          </body>
        </html>
        """,
        url="https://www.luogu.com.cn/problem/P1001",
    )

    assert "P1001 A+B Problem" in extracted
    assert "输入两个整数，输出它们的和。" in extracted


def test_discovery_service_extracts_codeforces_problem_statement_block() -> None:
    service = DiscoveryService()

    extracted = service.extract_reference_text(
        """
        <html>
          <body>
            <div class="problem-statement">
              <div class="title">A. Two Sum</div>
              <div class="input-specification"><p>The first line contains n.</p></div>
              <div class="output-specification"><p>Print the answer.</p></div>
            </div>
          </body>
        </html>
        """,
        url="https://codeforces.com/problemset/problem/1/A",
    )

    assert "A. Two Sum" in extracted
    assert "The first line contains n." in extracted
    assert "Print the answer." in extracted
