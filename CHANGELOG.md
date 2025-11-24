# Changelog

All notable changes to this project will be documented in this file.

## [0.27.0](https://github.com/Route-Sim/SPINE/compare/v0.26.0...v0.27.0) (2025-11-24)


### 🚀 Features

* **simulation:** implement statistics collection and tick rate warning system ([882688b](https://github.com/Route-Sim/SPINE/commit/882688bc48fbf67a0edd65e3f36d2d80e4704497))

## [0.26.0](https://github.com/Route-Sim/SPINE/compare/v0.25.4...v0.26.0) (2025-11-23)


### 🚀 Features

* **generation:** introduce parking generation parameters and enhance parking placement logic ([f8f1d23](https://github.com/Route-Sim/SPINE/commit/f8f1d2372fedf94db0d72078f398dd2de88ed653))

## [0.25.4](https://github.com/Route-Sim/SPINE/compare/v0.25.3...v0.25.4) (2025-11-23)


### 🐛 Bug Fixes

* **simulation:** add support for parking building statistics in map creation signals ([e2e0737](https://github.com/Route-Sim/SPINE/commit/e2e0737f61dc1a467197c7aeac1eca8b79690389))

## [0.25.3](https://github.com/Route-Sim/SPINE/compare/v0.25.2...v0.25.3) (2025-11-23)


### ♻️ Code Refactoring

* **simulation:** enhance simulation parameters handling with DTO integration ([a5b1337](https://github.com/Route-Sim/SPINE/commit/a5b133785531bafcaa30b9137b63456efb249224))

## [0.25.2](https://github.com/Route-Sim/SPINE/compare/v0.25.1...v0.25.2) (2025-11-23)


### ♻️ Code Refactoring

* **simulation:** replace legacy tick rate action ([eb58b85](https://github.com/Route-Sim/SPINE/commit/eb58b85607e2cafaf3b9c64e777496e6d6a55a87))

## [0.25.1](https://github.com/Route-Sim/SPINE/compare/v0.25.0...v0.25.1) (2025-11-23)


### 🐛 Bug Fixes

* **truck:** implement two-tier DTOs for selective state serialization ([187a74b](https://github.com/Route-Sim/SPINE/commit/187a74bd77812557dd4b52e1f172c50f40844b88))

## [0.25.0](https://github.com/Route-Sim/SPINE/compare/v0.24.0...v0.25.0) (2025-11-19)


### 🚀 Features

* **truck:** implement tachograph system for driving time and rest management ([f57df6f](https://github.com/Route-Sim/SPINE/commit/f57df6fd2f25858f24bac6a89982e605318e3eee))

## [0.24.0](https://github.com/Route-Sim/SPINE/compare/v0.23.0...v0.24.0) (2025-11-19)


### 🚀 Features

* **generation:** refactor map generation parameters to use Pydantic model for validation ([82108f4](https://github.com/Route-Sim/SPINE/commit/82108f418f32e1d52a8efb783c97b05aef743bd6))

## [0.23.0](https://github.com/Route-Sim/SPINE/compare/v0.22.0...v0.23.0) (2025-11-16)


### 🚀 Features

* **signal-dtos:** introduce type-safe DTOs for map creation signals ([f922886](https://github.com/Route-Sim/SPINE/commit/f9228860cff2f1622edecd91244303604b90926b))

## [0.22.0](https://github.com/Route-Sim/SPINE/compare/v0.21.3...v0.22.0) (2025-11-16)


### 🚀 Features

* **building:** enhance building.create action to support site buildings alongside parking buildings ([0f935bb](https://github.com/Route-Sim/SPINE/commit/0f935bb9434ea7c86b2e919e7b5a07db008cfb66))

## [0.21.3](https://github.com/Route-Sim/SPINE/compare/v0.21.2...v0.21.3) (2025-11-16)


### ♻️ Code Refactoring

* **queues:** remove deprecated action types for package creation and cancellation ([81b9c50](https://github.com/Route-Sim/SPINE/commit/81b9c50c93ffe9306a71207d4f9422e4ae674670))

## [0.21.2](https://github.com/Route-Sim/SPINE/compare/v0.21.1...v0.21.2) (2025-11-16)


### ♻️ Code Refactoring

* **tests:** remove state snapshot tests and related signal creation functions ([dea7a50](https://github.com/Route-Sim/SPINE/commit/dea7a50a5209c5426ffb0d886405c3bf02271128))

## [0.21.1](https://github.com/Route-Sim/SPINE/compare/v0.21.0...v0.21.1) (2025-11-15)


### ♻️ Code Refactoring

* **simulation:** update signal emissions to remove state snapshots ([ecfa3e4](https://github.com/Route-Sim/SPINE/commit/ecfa3e47c4cc69de296b6c984ecb1d819967615a))

## [0.21.0](https://github.com/Route-Sim/SPINE/compare/v0.20.0...v0.21.0) (2025-11-15)


### 🚀 Features

* **map:** enhance map creation to include complete graph snapshots with buildings ([2768194](https://github.com/Route-Sim/SPINE/commit/2768194bf0cdcc45a66e8a6516ac8dbb6f8e283c))

## [0.20.0](https://github.com/Route-Sim/SPINE/compare/v0.19.0...v0.20.0) (2025-11-15)


### 🚀 Features

* **building:** enhance building.create action to support multiple building types ([5427956](https://github.com/Route-Sim/SPINE/commit/542795620f82dcb8f87f2cba4334293e83691bdd))

## [0.19.0](https://github.com/Route-Sim/SPINE/compare/v0.18.0...v0.19.0) (2025-11-12)


### 🚀 Features

* **agent:** implement parking lifecycle for Truck transport agent ([0f1c87a](https://github.com/Route-Sim/SPINE/commit/0f1c87aa568ebdf74c0ff7cad1fde7879a17205b))

## [0.18.0](https://github.com/Route-Sim/SPINE/compare/v0.17.0...v0.18.0) (2025-11-12)


### 🚀 Features

* **building:** introduce Parking building type with capacity management and serialization ([43a2652](https://github.com/Route-Sim/SPINE/commit/43a2652f76af9d0fd4327a6c04c309dce0753d39))

## [0.17.0](https://github.com/Route-Sim/SPINE/compare/v0.16.0...v0.17.0) (2025-11-12)


### 🚀 Features

* **agent:** add route boundary metadata to Truck transport agent ([77a129e](https://github.com/Route-Sim/SPINE/commit/77a129ec15c6366f337df522e7e4eb5bdd828e39))

## [0.16.0](https://github.com/Route-Sim/SPINE/compare/v0.15.0...v0.16.0) (2025-11-12)


### 🚀 Features

* **agent:** add agent.list action and agent.listed signal for retrieving agent states ([2738f56](https://github.com/Route-Sim/SPINE/commit/2738f565c5ac926af49039bf9e202b589ac052c2))

## [0.15.0](https://github.com/Route-Sim/SPINE/compare/v0.14.1...v0.15.0) (2025-11-12)


### 🚀 Features

* **agent:** add agent.describe action and agent.described signal for full agent state retrieval ([cd335e1](https://github.com/Route-Sim/SPINE/commit/cd335e19ec2a4528750e2a055d6558a005308799))

## [0.14.1](https://github.com/Route-Sim/SPINE/compare/v0.14.0...v0.14.1) (2025-11-11)


### ♻️ Code Refactoring

* **generation:** implement speed limit logic for various road classes ([383fc0d](https://github.com/Route-Sim/SPINE/commit/383fc0d3bc1cd0a1553185d720611cd9d45880d1))

## [0.14.0](https://github.com/Route-Sim/SPINE/compare/v0.13.0...v0.14.0) (2025-11-08)


### 🚀 Features

* **agents:** introduce Truck transport agent with A* navigation and update routing services ([9e34957](https://github.com/Route-Sim/SPINE/commit/9e34957cadeb1bd49a0859957f1db470ebf5eeba))

## [0.13.0](https://github.com/Route-Sim/SPINE/compare/v0.12.1...v0.13.0) (2025-11-08)


### 🚀 Features

* **map:** introduce map creation signal with lightweight graph structure and update documentation ([f864a12](https://github.com/Route-Sim/SPINE/commit/f864a12f653952b65b41153b70c75a22130bb25d))

## [0.12.1](https://github.com/Route-Sim/SPINE/compare/v0.12.0...v0.12.1) (2025-11-08)


### ♻️ Code Refactoring

* **actions:** reorganize action handling with new structure and terminology ([28f2295](https://github.com/Route-Sim/SPINE/commit/28f2295d7dcc47824a9130a4d06664a8d429123b))

## [0.12.0](https://github.com/Route-Sim/SPINE/compare/v0.11.0...v0.12.0) (2025-11-08)


### 🚀 Features

* **map-generation:** enhance site placement in map generation ([c7af4da](https://github.com/Route-Sim/SPINE/commit/c7af4da642d301e6fa0fd5a4c41c1ace5283da3a))

## [0.11.0](https://github.com/Route-Sim/SPINE/compare/v0.10.1...v0.11.0) (2025-11-02)


### 🚀 Features

* **map-generation:** enhance procedural map generation with hierarchical structure ([956003e](https://github.com/Route-Sim/SPINE/commit/956003e013815f5fdd5c6ce5c36d0a31b8363337))

## [0.10.1](https://github.com/Route-Sim/SPINE/compare/v0.10.0...v0.10.1) (2025-11-01)


### ♻️ Code Refactoring

* **signals:** standardize signal format to use domain.signal structure ([7975bef](https://github.com/Route-Sim/SPINE/commit/7975befad1068494c476bd128e68d4d45f78db96))

## [0.10.0](https://github.com/Route-Sim/SPINE/compare/v0.9.0...v0.10.0) (2025-11-01)


### 🚀 Features

* **map-generation:** implement procedural map generation ([76f424c](https://github.com/Route-Sim/SPINE/commit/76f424c544b1befb1a73664b98c0547537e91b91))

## [0.9.0](https://github.com/Route-Sim/SPINE/compare/v0.8.0...v0.9.0) (2025-10-30)


### 🚀 Features

* **action:** implement action parsing and processing for simulation commands ([433fbfa](https://github.com/Route-Sim/SPINE/commit/433fbfac3679894c7dad35de7e0f400749d1d5ef))

## [0.8.0](https://github.com/Route-Sim/SPINE/compare/v0.7.0...v0.8.0) (2025-10-29)


### 🚀 Features

* **packages:** introduce Package and Site classes for logistics management ([2fee8a9](https://github.com/Route-Sim/SPINE/commit/2fee8a92925924631123877598f21c2895c70bdf))

## [0.7.0](https://github.com/Route-Sim/SPINE/compare/v0.6.0...v0.7.0) (2025-10-28)


### 🚀 Features

* **rules:** add project ground rules and typing guidelines for Python development ([f7883f8](https://github.com/Route-Sim/SPINE/commit/f7883f87a8a6ba98485c8a3802b9924df9bdf510))

## [0.6.0](https://github.com/Route-Sim/SPINE/compare/v0.5.0...v0.6.0) (2025-10-28)


### 🚀 Features

* **state-snapshot:** implement full state snapshot functionality ([071b9fa](https://github.com/Route-Sim/SPINE/commit/071b9fafd707d7f268bb7b94b534e50820b91fbe))

## [0.5.0](https://github.com/Route-Sim/SPINE/compare/v0.4.0...v0.5.0) (2025-10-26)


### 🚀 Features

* **maps:** implement map export and import functionality ([1c4afc9](https://github.com/Route-Sim/SPINE/commit/1c4afc92e6c28f148ec4cdd3e6761c19a907ed3f))

## [0.4.0](https://github.com/Route-Sim/SPINE/compare/v0.3.0...v0.4.0) (2025-10-26)


### 🚀 Features

* **buildings:** introduce Building and BuildingAgent classes ([c36c32b](https://github.com/Route-Sim/SPINE/commit/c36c32b21677f56860ed33807f02dfcfe1eac8d2))


### 🐛 Bug Fixes

* **tests:** update pytest configuration and enhance WebSocket server tests ([f571ba4](https://github.com/Route-Sim/SPINE/commit/f571ba47cec66da85ed2c97cdff0759f68320165))

## [0.3.0](https://github.com/Route-Sim/SPINE/compare/v0.2.0...v0.3.0) (2025-10-26)


### 🚀 Features

* **simulation:** enhance simulation runner with uvicorn server lifecycle management ([3e1b504](https://github.com/Route-Sim/SPINE/commit/3e1b504530e8b1bbf81d03eeef7bccc25196afc0))

## [0.2.0](https://github.com/Route-Sim/SPINE/compare/v0.1.0...v0.2.0) (2025-10-25)


### 🚀 Features

* **docker:** add Docker support with multi-stage builds and Docker Compose configuration ([96750c1](https://github.com/Route-Sim/SPINE/commit/96750c1a7c713e83d218f9738239d951f6f2452c))

## 0.1.0 (2025-10-25)


### 🚀 Features

* **agents:** implement AgentBase class and World management system ([c66d85a](https://github.com/Route-Sim/SPINE/commit/c66d85a93cc4de79b4cd2560a879d1d25650c008))
* **conventional-commits:** add commit message validation and semantic release configuration ([9f5efc3](https://github.com/Route-Sim/SPINE/commit/9f5efc37238c7232aee31a8996fec0cb89cd6060))
* enhance simulation framework with new agent types, WebSocket server, and documentation updates ([312a937](https://github.com/Route-Sim/SPINE/commit/312a937a4247156565ca52b5e5694dd7414c3c23))
