# Changelog

## [1.0.0](https://github.com/echohello-dev/yap-on-slack/compare/yap-on-slack-v0.0.1...yap-on-slack-v1.0.0) (2026-01-05)


### ⚠ BREAKING CHANGES

* **cli:** The version of the package has been downgraded to 0.0.1.
* **config:** The configuration loading mechanism has changed to accommodate multi-user setups, requiring updates to existing environment variable configurations.

### Features

* add ADR for using Slack Session Tokens instead of Bot API ([e961af4](https://github.com/echohello-dev/yap-on-slack/commit/e961af41e3e8ba3ae5669b9992c1e530ebec005e))
* add export-only mode, intelligent throttling, and improved file naming ([ffd51f7](https://github.com/echohello-dev/yap-on-slack/commit/ffd51f7f3f0c1072e63f8699c469c07d4717b45f))
* add GitHub Actions workflows and troubleshooting guide ([53c6f51](https://github.com/echohello-dev/yap-on-slack/commit/53c6f511385215f71d413f739359200e840e6771))
* add Slack bot token (xoxb) authentication support ([64132a2](https://github.com/echohello-dev/yap-on-slack/commit/64132a2b334e66bfa0c35ba8a227fbb21c6aaef5))
* add SSL strict X509 control with auto-disable for custom CA bundles ([b27c32d](https://github.com/echohello-dev/yap-on-slack/commit/b27c32d8d06f32ce1be43c0c40a90cd3181dd5bb))
* **ci:** add GitHub Actions workflow for publishing and Docker builds ([1d94645](https://github.com/echohello-dev/yap-on-slack/commit/1d94645fac2f368988a2c98fc7a4aff7050b6a90))
* **cli:** add channel scanning command to generate system prompts ([900f3b7](https://github.com/echohello-dev/yap-on-slack/commit/900f3b7c2c83e6e247d8a09c168c973943bb0596))
* **cli:** add commands to show config template and JSON schema ([58ea7ac](https://github.com/echohello-dev/yap-on-slack/commit/58ea7acc0a7d42c6cba2133904dbe84b067c4c60))
* **cli:** add interactive channel selector for message posting ([1e706a4](https://github.com/echohello-dev/yap-on-slack/commit/1e706a4f418ea55d78e868c17e3cdd03de7a551a))
* **cli:** add SSL configuration options for channel scanning ([d4e6cf0](https://github.com/echohello-dev/yap-on-slack/commit/d4e6cf00f4601a858d912c22b9ba8b2407613573))
* **config:** add multi-user support and improve message handling ([32182e1](https://github.com/echohello-dev/yap-on-slack/commit/32182e19e7c3022691177e7f3c82c3424b097603))
* **config:** consolidate configuration files into unified config.yaml ([51d5fb1](https://github.com/echohello-dev/yap-on-slack/commit/51d5fb1b2f6ac5bf1f0a297f34d6a40234ad8d5a))
* **config:** enhance configuration discovery and validation logic ([9a0758e](https://github.com/echohello-dev/yap-on-slack/commit/9a0758e232b2bc0c79cd24f399f8b9f24a7fea14))
* **dev:** add types-PyYAML to development dependencies ([eb1f1cf](https://github.com/echohello-dev/yap-on-slack/commit/eb1f1cf9bc498cb5660bf7a69d33012d4d9f9406))
* **docs:** add contributing guidelines and pre-commit setup instructions ([2254d88](https://github.com/echohello-dev/yap-on-slack/commit/2254d885bef9fa4ccb46a9dc3039f37590c7bdda))
* enhance AI message generation and configuration ([af9fd74](https://github.com/echohello-dev/yap-on-slack/commit/af9fd74aaa913290a43d0ff573e56b64a98e4bdf))
* enhance CLI functionality and improve documentation ([b6382c8](https://github.com/echohello-dev/yap-on-slack/commit/b6382c876a576a55d8db047dbfc771a4f514018e))
* Enhance Slack message posting functionality with improved error handling and validation ([ca9ffaa](https://github.com/echohello-dev/yap-on-slack/commit/ca9ffaa57cadbb4eda721b21842eec4e24da9295))
* enhance version command with commit SHA deeplink ([bd66f38](https://github.com/echohello-dev/yap-on-slack/commit/bd66f38d3a5e0ec720d2caa8f437b357f643271f))
* **github:** add enhanced GitHub context integration and filtering options ([be8c2b7](https://github.com/echohello-dev/yap-on-slack/commit/be8c2b7f3627a65483247a24fd26007a22b34aca))
* **github:** add GitHub context integration for AI message generation ([14fb952](https://github.com/echohello-dev/yap-on-slack/commit/14fb95207a16b03f0551b7b49cc72521bb324c1d))
* make throttling range configurable and update documentation ([6764e6a](https://github.com/echohello-dev/yap-on-slack/commit/6764e6a075eca4340385aaf03c7cd2cff4a8cacc))
* **ssl:** add SSL context management for API calls ([8120be7](https://github.com/echohello-dev/yap-on-slack/commit/8120be70479c23996707cc7a8c85587ba1ec9be7))
* **ssl:** add SSL/TLS support with configuration options ([a446c2b](https://github.com/echohello-dev/yap-on-slack/commit/a446c2ba6c46322b538c63ad973aa1fb19e39a63))
* **ssl:** enable SSL verification for API requests ([ea53e6d](https://github.com/echohello-dev/yap-on-slack/commit/ea53e6d81efed0e9737f928c0c93ca447697e3e7))
* **tests:** add comprehensive unit and integration tests for message handling ([a5427a5](https://github.com/echohello-dev/yap-on-slack/commit/a5427a5ca3d6862a974b3b1db3ac8e7cf324eb1d))
* **tests:** add user mention and broadcast mention tests ([63a6ac6](https://github.com/echohello-dev/yap-on-slack/commit/63a6ac6d9f20fe332ee7afb86cd17d6837342c60))


### Bug Fixes

* add type annotation to satisfy mypy ([28b87a1](https://github.com/echohello-dev/yap-on-slack/commit/28b87a11eb80101c6ec610e4272e5cab9906f919))
* **ci:** add missing release-please manifest file ([5e38230](https://github.com/echohello-dev/yap-on-slack/commit/5e382307768e9de218377b964462c5887f7b14c5))
* copy README.md in Dockerfile for package build ([94bc01c](https://github.com/echohello-dev/yap-on-slack/commit/94bc01cba72825b82264c27c0c742ef339cb7775))
* copy source code before installing package in Docker ([a497de4](https://github.com/echohello-dev/yap-on-slack/commit/a497de4e43b6b48db0f1ef1a31210594e6a1c286))
* format imports for ruff linting ([94d5714](https://github.com/echohello-dev/yap-on-slack/commit/94d5714169762c3bfc6438bafbec67e12d9d8f14))
* **github:** specify type for commit_params in get_github_context function ([fab63d1](https://github.com/echohello-dev/yap-on-slack/commit/fab63d15f0838bb423964f52d0a7f65cae80d543))
* resolve linting and type checking issues ([4cc17c8](https://github.com/echohello-dev/yap-on-slack/commit/4cc17c8bb0abce5d0005092545688b48477e742f))


### Documentation

* add ADR for using XDG config standard instead of platformdirs ([fe4262b](https://github.com/echohello-dev/yap-on-slack/commit/fe4262b56c337fb38278ecd96cac903dce5fa7b9))
* add ADRs for unified config.yaml and channel scanning features ([ca8e300](https://github.com/echohello-dev/yap-on-slack/commit/ca8e30029382640c4e85bb3ab3a94f5285933a50))
* add comprehensive security documentation for Slack session tokens ([eaddfcb](https://github.com/echohello-dev/yap-on-slack/commit/eaddfcbe551597f85e2a0181f06baeb89004db5d))
* add comprehensive security documentation for Slack session tokens ([c8ea7d8](https://github.com/echohello-dev/yap-on-slack/commit/c8ea7d8e316f7668e30dd089d3455229dd19e1bf))
* enhance GitHub Actions troubleshooting guidance ([ff21228](https://github.com/echohello-dev/yap-on-slack/commit/ff21228609844bc4bb5a333ab91b86c02b9bf341))
* enhance GitHub Actions troubleshooting instructions ([f374e13](https://github.com/echohello-dev/yap-on-slack/commit/f374e133db2e6142e53748f892923d8922fdf2e6))
* enhance troubleshooting instructions for GitHub Actions ([5ef201e](https://github.com/echohello-dev/yap-on-slack/commit/5ef201e2e3621ab1e62ecb4b6008e9c57aaab8ca))
* update AGENTS.md for improved structure and clarity ([dbe03a1](https://github.com/echohello-dev/yap-on-slack/commit/dbe03a1aa9fbf025a61c67fe6ac13bf0dce4fd1b))
