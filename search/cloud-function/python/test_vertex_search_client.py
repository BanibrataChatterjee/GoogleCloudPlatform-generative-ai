# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import json
from unittest.mock import MagicMock, patch

from enums import EngineChunkType, EngineDataType, SummaryType
from google.cloud import discoveryengine_v1alpha as discoveryengine
from google.cloud.discoveryengine_v1alpha.services.search_service.pagers import (
    SearchPager,
)
from google.cloud.discoveryengine_v1alpha.types import Document, SearchResponse
import pytest
from vertex_search_client import VertexSearchClient


class DerivedStructData:
    def __init__(self, title, link, extractive_answers, snippets):
        self.title = title
        self.link = link
        self.extractive_answers = extractive_answers
        self.snippets = snippets


def create_mock_search_pager_result():
    mock_pager = MagicMock(spec=SearchPager)
    mock_pager.__iter__.return_value = [create_mock_search_pager_return_value()]
    mock_pager.total_size = 1
    mock_pager.attribution_token = "test-token"
    mock_pager.next_page_token = "next-page"
    mock_pager.corrected_query = "corrected query"
    mock_pager.summary = SearchResponse.Summary(summary_text="Test summary")
    mock_pager.applied_controls = None
    mock_pager.facets = []
    mock_pager.guided_search_result = []
    mock_pager.query_expansion_info = []
    return mock_pager


def create_mock_search_pager_return_value():
    search_result = SearchResponse.SearchResult()
    document = Document()

    derived_struct_data = {
        "title": "Employee Benefits Summary",
        "link": "gs://company-docs/Employee_Benefits_Summary.pdf",
        "extractive_answers": [{"content": "Test content", "pageNumber": "1"}],
        "snippets": [{"snippet_status": "SUCCESS", "snippet": "Test snippet"}],
    }

    # Set the derived_struct_data field of the document
    document.derived_struct_data = derived_struct_data

    search_result.document = document
    return search_result


@pytest.fixture
def mock_search_service_client():
    with patch(
        "vertex_search_client.discoveryengine.SearchServiceClient"
    ) as mock_client:
        mock_client.return_value.serving_config_path.return_value = (
            "projects/test-project/locations/us-central1/dataStores/test-data-store/"
            "servingConfigs/default_config"
        )
        yield mock_client


@pytest.fixture
def vertex_search_client(mock_search_service_client):
    return VertexSearchClient(
        project_id="test-project",
        location="us-central1",
        data_store_id="test-data-store",
        engine_data_type=EngineDataType.UNSTRUCTURED,
        engine_chunk_type=EngineChunkType.DOCUMENT_WITH_EXTRACTIVE_SEGMENTS,
        summary_type=SummaryType.VERTEX_AI_SEARCH,
    )


def test_init(mock_search_service_client):
    client = VertexSearchClient(
        project_id="test-project",
        location="us-central1",
        data_store_id="test-data-store",
        engine_data_type=EngineDataType.UNSTRUCTURED,
        engine_chunk_type=EngineChunkType.DOCUMENT_WITH_EXTRACTIVE_SEGMENTS,
        summary_type=SummaryType.VERTEX_AI_SEARCH,
    )

    assert client.project_id == "test-project"
    assert client.location == "us-central1"
    assert client.data_store_id == "test-data-store"
    assert client.engine_data_type == EngineDataType.UNSTRUCTURED
    assert client.engine_chunk_type == EngineChunkType.DOCUMENT_WITH_EXTRACTIVE_SEGMENTS
    assert client.summary_type == SummaryType.VERTEX_AI_SEARCH

    mock_search_service_client.assert_called_once()


def test_get_serving_config(vertex_search_client):
    expected_serving_config = (
        "projects/test-project/locations/us-central1/dataStores/test-data-store/"
        "servingConfigs/default_config"
    )
    assert vertex_search_client.serving_config == expected_serving_config


def test_build_search_request(vertex_search_client):
    query = "test query"
    page_size = 5
    request = vertex_search_client._build_search_request(query, page_size)

    assert isinstance(request, discoveryengine.SearchRequest)
    assert request.serving_config == vertex_search_client.serving_config
    assert request.query == query
    assert request.page_size == page_size

    assert (
        request.query_expansion_spec.condition
        == discoveryengine.SearchRequest.QueryExpansionSpec.Condition.AUTO
    )
    assert (
        request.spell_correction_spec.mode
        == discoveryengine.SearchRequest.SpellCorrectionSpec.Mode.AUTO
    )

    assert request.content_search_spec.snippet_spec.return_snippet is True
    assert request.content_search_spec.summary_spec.summary_result_count == 5
    assert request.content_search_spec.summary_spec.include_citations is True
    assert request.content_search_spec.summary_spec.ignore_adversarial_query is True
    assert (
        request.content_search_spec.summary_spec.ignore_non_summary_seeking_query
        is True
    )
    assert (
        request.content_search_spec.extractive_content_spec.max_extractive_answer_count
        == 1
    )
    assert (
        request.content_search_spec.extractive_content_spec.return_extractive_segment_score
        is True
    )


def test_map_search_pager_to_dict_basic(vertex_search_client):
    mock_pager = create_mock_search_pager_result()

    result = vertex_search_client._map_search_pager_to_dict(mock_pager)

    assert "results" in result
    assert len(result["results"]) == 1
    assert result["total_size"] == 1
    assert result["attribution_token"] == "test-token"
    assert result["next_page_token"] == "next-page"
    assert result["corrected_query"] == "corrected query"
    assert result["summary"]["summary_text"] == "Test summary"


def test_map_search_pager_to_dict_document_content(vertex_search_client):
    mock_pager = create_mock_search_pager_result()

    result = vertex_search_client._map_search_pager_to_dict(mock_pager)

    document = result["results"][0]["document"]
    assert document["derived_struct_data"]["title"] == "Employee Benefits Summary"
    assert (
        document["derived_struct_data"]["link"]
        == "gs://company-docs/Employee_Benefits_Summary.pdf"
    )
    assert len(document["derived_struct_data"]["extractive_answers"]) == 1
    assert (
        document["derived_struct_data"]["extractive_answers"][0]["content"]
        == "Test content"
    )
    assert len(document["derived_struct_data"]["snippets"]) == 1
    assert document["derived_struct_data"]["snippets"][0]["snippet"] == "Test snippet"


def test_parse_chunk_result(vertex_search_client):
    chunk = {
        "id": "chunk1",
        "relevance_score": 0.95,
        "content": "Test content",
        "document_metadata": {"title": "Test Title", "uri": "https://example.com"},
        "page_span": {"page_start": 1, "page_end": 2},
    }

    result = vertex_search_client._parse_chunk_result(chunk)

    assert result["page_content"] == "Test content"
    assert result["metadata"]["chunk_id"] == "chunk1"
    assert result["metadata"]["score"] == 0.95
    assert result["metadata"]["title"] == "Test Title"
    assert result["metadata"]["uri"] == "https://example.com"
    assert result["metadata"]["page"] == 1
    assert result["metadata"]["page_span_end"] == 2


def test_strip_content():
    input_text = "<p>Test <strong>content</strong> with &quot;quotes&quot;</p>"
    expected_output = 'Test content with "quotes"'
    assert VertexSearchClient._strip_content(input_text) == expected_output


def test_simplify_search_results_mixed_chunk_and_segments(vertex_search_client):
    input_dict = {
        "results": [
            {"document": {"id": "doc1", "derived_struct_data": {"title": "Test"}}},
            {"chunk": {"id": "chunk1", "content": "Test content"}},
        ]
    }

    result = vertex_search_client._simplify_search_results(input_dict)

    assert "simplified_results" in result
    assert len(result["simplified_results"]) == 2
    assert "metadata" in result["simplified_results"][0]
    assert "page_content" in result["simplified_results"][1]


def test_parse_document_result(vertex_search_client):
    document = {
        "id": "doc1",
        "derived_struct_data": {
            "title": "Employee Benefits Summary",
            "extractive_answers": [
                {
                    "content": "High Deductible HMO • Premiums: Lower premiums at $150 per month. • Deductibles: High at $2000. • Out-of-Pocket Maximums: Higher limit of $6500.",
                    "page_number": "3",
                }
            ],
            "snippets": [
                {
                    "snippet_status": "SUCCESS",
                    "snippet": "... <b>per month</b>, due to flexibility and network size. • Deductibles: Moderate at $1,000, offering <b>a</b> balance between <b>cost</b> and <b>coverage</b>. ...",
                }
            ],
            "link": "gs://company-docs/Employee_Benefits_Summary.pdf",
        },
    }

    result = vertex_search_client._parse_document_result(document)

    assert result["metadata"]["title"] == "Employee Benefits Summary"
    assert (
        result["metadata"]["link"] == "gs://company-docs/Employee_Benefits_Summary.pdf"
    )
    assert "page_content" in result
    assert "High Deductible HMO" in result["page_content"]
    assert "On page 3" in result["page_content"]


@patch("vertex_search_client.VertexSearchClient._map_search_pager_to_dict")
@patch("vertex_search_client.VertexSearchClient._simplify_search_results")
def test_search(
    mock_simplify, mock_map_pager, vertex_search_client, mock_search_service_client
):
    mock_pager = create_mock_search_pager_result()

    mock_search_service_client.return_value.search.return_value = mock_pager

    mock_map_pager.return_value = {"results": [{"document": {"id": "doc1"}}]}
    mock_simplify.return_value = {"simplified_results": [{"id": "doc1"}]}

    results = vertex_search_client.search("test query")

    mock_search_service_client.return_value.search.assert_called_once()
    mock_map_pager.assert_called_once_with(mock_pager)
    mock_simplify.assert_called_once_with({"results": [{"document": {"id": "doc1"}}]})
    assert results == {"simplified_results": [{"id": "doc1"}]}

    results_json = json.dumps(results)
    assert results_json == '{"simplified_results": [{"id": "doc1"}]}'
