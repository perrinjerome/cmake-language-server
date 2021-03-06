from concurrent import futures
from pathlib import Path
from typing import Optional

from pygls.features import (COMPLETION, FORMATTING, HOVER, INITIALIZE,
                            TEXT_DOCUMENT_DID_OPEN)
from pygls.server import LanguageServer
from pygls.types import (CompletionContext, CompletionParams,
                         CompletionTriggerKind, DidOpenTextDocumentParams,
                         DocumentFormattingParams, FormattingOptions,
                         InitializeParams, Position, TextDocumentIdentifier,
                         TextDocumentItem, TextDocumentPositionParams)

CALL_TIMEOUT = 2


def _init(client: LanguageServer, root: Path):
    retry = 3
    while retry > 0:
        try:
            client.lsp.send_request(
                INITIALIZE,
                InitializeParams(
                    process_id=1234, root_uri=root.as_uri(),
                    capabilities=None)).result(timeout=CALL_TIMEOUT)
        except futures.TimeoutError:
            retry -= 1
        else:
            break


def _open(client: LanguageServer, path: Path, text: Optional[str] = None):
    if text is None:
        with open(path) as fp:
            text = fp.read()

    client.lsp.notify(
        TEXT_DOCUMENT_DID_OPEN,
        DidOpenTextDocumentParams(
            TextDocumentItem(path.as_uri(), 'cmake', 1, text)))


def test_initialize(client_server, datadir):
    client, server = client_server

    assert server._api is None
    _init(client, datadir)
    assert server._api is not None


def test_completions_invoked(client_server, datadir):
    client, server = client_server
    _init(client, datadir)
    path = datadir / 'CMakeLists.txt'
    _open(client, path, 'projec')
    response = client.lsp.send_request(
        COMPLETION,
        CompletionParams(TextDocumentIdentifier(path.as_uri()), Position(
            0, 6), CompletionContext(
                CompletionTriggerKind.Invoked))).result(timeout=CALL_TIMEOUT)
    item = next(filter(lambda x: x.label == 'project', response.items), None)
    assert item is not None
    assert '<PROJECT-NAME>' in item.documentation


def test_completions_triggercharacter_variable(client_server, datadir):
    client, server = client_server
    _init(client, datadir)
    path = datadir / 'CMakeLists.txt'
    _open(client, path, '${')
    response = client.lsp.send_request(
        COMPLETION,
        CompletionParams(
            TextDocumentIdentifier(path.as_uri()), Position(0, 2),
            CompletionContext(CompletionTriggerKind.TriggerCharacter,
                              '{'))).result(timeout=CALL_TIMEOUT)
    assert 'PROJECT_VERSION' in [x.label for x in response.items]


def test_completions_triggercharacter_module(client_server, datadir):
    client, server = client_server
    _init(client, datadir)
    path = datadir / 'CMakeLists.txt'
    _open(client, path, 'include(')
    response = client.lsp.send_request(
        COMPLETION,
        CompletionParams(
            TextDocumentIdentifier(path.as_uri()), Position(0, 8),
            CompletionContext(CompletionTriggerKind.TriggerCharacter,
                              '('))).result(timeout=CALL_TIMEOUT)
    assert 'GoogleTest' in [x.label for x in response.items]


def test_completions_triggercharacter_package(client_server, datadir):
    client, server = client_server
    _init(client, datadir)
    path = datadir / 'CMakeLists.txt'
    _open(client, path, 'find_package(')
    response = client.lsp.send_request(
        COMPLETION,
        CompletionParams(
            TextDocumentIdentifier(path.as_uri()), Position(0, 13),
            CompletionContext(CompletionTriggerKind.TriggerCharacter,
                              '('))).result(timeout=CALL_TIMEOUT)
    assert 'Boost' in [x.label for x in response.items]


def test_formatting(client_server, datadir):
    client, server = client_server
    _init(client, datadir)
    path = datadir / 'CMakeLists.txt'
    _open(client, path, 'a ( b c ) ')
    response = client.lsp.send_request(
        FORMATTING,
        DocumentFormattingParams(TextDocumentIdentifier(path.as_uri()),
                                 FormattingOptions(
                                     2, True))).result(timeout=CALL_TIMEOUT)
    assert response[0].newText == 'a(b c)\n'


def test_hover(client_server, datadir):
    client, server = client_server
    _init(client, datadir)
    path = datadir / 'CMakeLists.txt'
    _open(client, path, 'project()')
    response = client.lsp.send_request(
        HOVER,
        TextDocumentPositionParams(TextDocumentIdentifier(path.as_uri()),
                                   Position())).result(timeout=CALL_TIMEOUT)
    assert '<PROJECT-NAME>' in response.contents.value
