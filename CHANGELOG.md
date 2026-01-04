# Changelog

## [2.0.0](https://github.com/echohello-dev/yap-on-slack/compare/yap-on-slack-v1.0.0...yap-on-slack-v2.0.0) (2026-01-04)


### ⚠ BREAKING CHANGES

* **config:** The configuration loading mechanism has changed to accommodate multi-user setups, requiring updates to existing environment variable configurations.

### Features

* add ADR for using Slack Session Tokens instead of Bot API ([e961af4](https://github.com/echohello-dev/yap-on-slack/commit/e961af41e3e8ba3ae5669b9992c1e530ebec005e))
* add GitHub Actions workflows and troubleshooting guide ([53c6f51](https://github.com/echohello-dev/yap-on-slack/commit/53c6f511385215f71d413f739359200e840e6771))
* **config:** add multi-user support and improve message handling ([32182e1](https://github.com/echohello-dev/yap-on-slack/commit/32182e19e7c3022691177e7f3c82c3424b097603))
* **config:** consolidate configuration files into unified config.yaml ([51d5fb1](https://github.com/echohello-dev/yap-on-slack/commit/51d5fb1b2f6ac5bf1f0a297f34d6a40234ad8d5a))
* **config:** enhance configuration discovery and validation logic ([9a0758e](https://github.com/echohello-dev/yap-on-slack/commit/9a0758e232b2bc0c79cd24f399f8b9f24a7fea14))
* **dev:** add types-PyYAML to development dependencies ([eb1f1cf](https://github.com/echohello-dev/yap-on-slack/commit/eb1f1cf9bc498cb5660bf7a69d33012d4d9f9406))
* **docs:** add contributing guidelines and pre-commit setup instructions ([2254d88](https://github.com/echohello-dev/yap-on-slack/commit/2254d885bef9fa4ccb46a9dc3039f37590c7bdda))
* enhance CLI functionality and improve documentation ([b6382c8](https://github.com/echohello-dev/yap-on-slack/commit/b6382c876a576a55d8db047dbfc771a4f514018e))
* Enhance Slack message posting functionality with improved error handling and validation ([ca9ffaa](https://github.com/echohello-dev/yap-on-slack/commit/ca9ffaa57cadbb4eda721b21842eec4e24da9295))
* **tests:** add comprehensive unit and integration tests for message handling ([a5427a5](https://github.com/echohello-dev/yap-on-slack/commit/a5427a5ca3d6862a974b3b1db3ac8e7cf324eb1d))
* **tests:** add user mention and broadcast mention tests ([63a6ac6](https://github.com/echohello-dev/yap-on-slack/commit/63a6ac6d9f20fe332ee7afb86cd17d6837342c60))


### Bug Fixes

* add type annotation to satisfy mypy ([28b87a1](https://github.com/echohello-dev/yap-on-slack/commit/28b87a11eb80101c6ec610e4272e5cab9906f919))
* **ci:** add missing release-please manifest file ([5e38230](https://github.com/echohello-dev/yap-on-slack/commit/5e382307768e9de218377b964462c5887f7b14c5))
* copy README.md in Dockerfile for package build ([94bc01c](https://github.com/echohello-dev/yap-on-slack/commit/94bc01cba72825b82264c27c0c742ef339cb7775))
* copy source code before installing package in Docker ([a497de4](https://github.com/echohello-dev/yap-on-slack/commit/a497de4e43b6b48db0f1ef1a31210594e6a1c286))
* format imports for ruff linting ([94d5714](https://github.com/echohello-dev/yap-on-slack/commit/94d5714169762c3bfc6438bafbec67e12d9d8f14))


### Documentation

* add comprehensive security documentation for Slack session tokens ([eaddfcb](https://github.com/echohello-dev/yap-on-slack/commit/eaddfcbe551597f85e2a0181f06baeb89004db5d))
* add comprehensive security documentation for Slack session tokens ([c8ea7d8](https://github.com/echohello-dev/yap-on-slack/commit/c8ea7d8e316f7668e30dd089d3455229dd19e1bf))
* enhance GitHub Actions troubleshooting guidance ([ff21228](https://github.com/echohello-dev/yap-on-slack/commit/ff21228609844bc4bb5a333ab91b86c02b9bf341))
* enhance GitHub Actions troubleshooting instructions ([f374e13](https://github.com/echohello-dev/yap-on-slack/commit/f374e133db2e6142e53748f892923d8922fdf2e6))
* enhance troubleshooting instructions for GitHub Actions ([5ef201e](https://github.com/echohello-dev/yap-on-slack/commit/5ef201e2e3621ab1e62ecb4b6008e9c57aaab8ca))
