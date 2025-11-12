# Changelog

All notable changes to this project will be documented in this file.

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
