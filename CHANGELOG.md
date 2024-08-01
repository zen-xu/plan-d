# Changelog

All notable changes to this project will be documented in this file.

## [0.2.0](https://github.com/zen-xu/plan_d/compare/0.1.0..0.2.0) - 2024-08-01

### 🚀  Features

- Support to disable magic command ([#36](https://github.com/zen-xu/plan_d/issues/36)) - ([eda8a9c](https://github.com/zen-xu/plan_d/commit/eda8a9c522468cce011913d490c0d13b72b9aa66))

### 🐛 Bug Fixes

- Magic result not in new line ([#34](https://github.com/zen-xu/plan_d/issues/34)) - ([3ebbfa6](https://github.com/zen-xu/plan_d/commit/3ebbfa62e3d7219c8a528fb9dfda18b3c6cb476b))
- Magic command output may contain ansi color codes ([#33](https://github.com/zen-xu/plan_d/issues/33)) - ([2e7d191](https://github.com/zen-xu/plan_d/commit/2e7d19117dacc6c4bcf72ef3da39cb87e0a3cc20))

### 🚜 Refactor

- Print magic result plain text ([#35](https://github.com/zen-xu/plan_d/issues/35)) - ([6706be5](https://github.com/zen-xu/plan_d/commit/6706be5f1d44b3baae25f3445dea3b933c919658))

### 📚 Documentation

- Update README.md ([#31](https://github.com/zen-xu/plan_d/issues/31)) - ([84f96d6](https://github.com/zen-xu/plan_d/commit/84f96d6385ff190a5936fab3671c2d494fa015c2))

## [0.1.0] - 2024-08-01

### 🚀  Features

- Impl `launch_pland_on_exception` to auto launch debugger ([#25](https://github.com/zen-xu/plan_d/issues/25)) - ([85b3988](https://github.com/zen-xu/plan_d/commit/85b3988f4c6f158bf30990da53811c1cd7d1b56b))
- Use rich to beautify trace ([#17](https://github.com/zen-xu/plan_d/issues/17)) - ([b3a4a00](https://github.com/zen-xu/plan_d/commit/b3a4a00c3c8a5eeaed099a4df5bc427b490a5e28))
- Impl post_mortem ([#16](https://github.com/zen-xu/plan_d/issues/16)) - ([9f068ea](https://github.com/zen-xu/plan_d/commit/9f068ea8206154cd3ca5aa99a2d1ee7ea747e241))
- Add new cmds (v)ars, varstree/(vt), (i)nspect, inspectall/(ia) ([#15](https://github.com/zen-xu/plan_d/issues/15)) - ([8f96794](https://github.com/zen-xu/plan_d/commit/8f96794f187211185c33d8ffe5480f5bf7082d1f))
- Method `message` default enable soft_wrap ([#14](https://github.com/zen-xu/plan_d/issues/14)) - ([473776a](https://github.com/zen-xu/plan_d/commit/473776aed1b8ca7b90fb7e19c5f7de204538f970))
- Support adaptive client terminal size ([#11](https://github.com/zen-xu/plan_d/issues/11)) - ([26d4faa](https://github.com/zen-xu/plan_d/commit/26d4faab599413f8deea467c1c94958ca5df8dae))
- Beautify help info ([#10](https://github.com/zen-xu/plan_d/issues/10)) - ([8b352af](https://github.com/zen-xu/plan_d/commit/8b352afca6381581e223449237f57ca7a05f8461))
- Ban pdb command `list` ([#9](https://github.com/zen-xu/plan_d/issues/9)) - ([eaa6bad](https://github.com/zen-xu/plan_d/commit/eaa6bad20bbcacdfa5d607f27031bc049bc84787))
- Support use rich for better display ([#8](https://github.com/zen-xu/plan_d/issues/8)) - ([bf504b5](https://github.com/zen-xu/plan_d/commit/bf504b57e67a3bcd2309a41a03600c8e05ec0f3a))
- Support IPython magic func ([#4](https://github.com/zen-xu/plan_d/issues/4)) - ([8e6a97e](https://github.com/zen-xu/plan_d/commit/8e6a97e6ed5adc799d49b55c946ea0589eb82a88))
- Impl remote debugger ([#3](https://github.com/zen-xu/plan_d/issues/3)) - ([59978ab](https://github.com/zen-xu/plan_d/commit/59978ab7ccdb0a407ff50124d8d1f22f26cd3488))

### 🐛 Bug Fixes

- Fix update changelog script ([#30](https://github.com/zen-xu/plan_d/issues/30)) - ([7e5c7d0](https://github.com/zen-xu/plan_d/commit/7e5c7d032ea37325d2956d9270fafc140bed3626))
- Fix default rich console size when connected ([#12](https://github.com/zen-xu/plan_d/issues/12)) - ([5824ce6](https://github.com/zen-xu/plan_d/commit/5824ce696eb81f8ab6507b7387b2350bc71ec302))
- Fix can't show long module source ([#7](https://github.com/zen-xu/plan_d/issues/7)) - ([37b2920](https://github.com/zen-xu/plan_d/commit/37b292048152e0c0bb413ee9c21e0f616c6e5a84))

### 🚜 Refactor

- Optimize pinfo command ([#22](https://github.com/zen-xu/plan_d/issues/22)) - ([770fca1](https://github.com/zen-xu/plan_d/commit/770fca1221a418f8de9f9e202a4c35b52aea65be))
- Support method `message` pass extra console.print args ([#13](https://github.com/zen-xu/plan_d/issues/13)) - ([860674d](https://github.com/zen-xu/plan_d/commit/860674d1875f7798bd5a4edc3e0979a5b92debe9))
- Redirect stdout and stderr ([#6](https://github.com/zen-xu/plan_d/issues/6)) - ([6fa006e](https://github.com/zen-xu/plan_d/commit/6fa006e11841a40ec5719a1941b5bdb5db01ac10))

### 🎨 Styling

- *(ruff)* Disable force-single-line ([#24](https://github.com/zen-xu/plan_d/issues/24)) - ([72aae37](https://github.com/zen-xu/plan_d/commit/72aae370de785014a97188c004b135cc627e13d9))

### ⚙️ Miscellaneous Tasks

- Add release ci ([#28](https://github.com/zen-xu/plan_d/issues/28)) - ([f76a744](https://github.com/zen-xu/plan_d/commit/f76a7448929e2e6d13451bfad55a02bc5fc0b350))
- Add release ci ([#28](https://github.com/zen-xu/plan_d/issues/28)) - ([e7e5ee1](https://github.com/zen-xu/plan_d/commit/e7e5ee19e654ff5b3451fd879aabbc285ccc5294))
- Specify suppress when print exception ([#26](https://github.com/zen-xu/plan_d/issues/26)) - ([4b41287](https://github.com/zen-xu/plan_d/commit/4b41287befa8315d9e57d56fcef83ec5b2ca3104))
- Change inspect source style ([#23](https://github.com/zen-xu/plan_d/issues/23)) - ([0d3bee3](https://github.com/zen-xu/plan_d/commit/0d3bee3a3621e9304e12ae1fd0b04221c9c50203))
- Update cSpell words ([#21](https://github.com/zen-xu/plan_d/issues/21)) - ([52d4b6d](https://github.com/zen-xu/plan_d/commit/52d4b6d6702d0e199e4c6a506a87fd29e1b1ffc2))
- Update cSpell words ([#20](https://github.com/zen-xu/plan_d/issues/20)) - ([0b9d25a](https://github.com/zen-xu/plan_d/commit/0b9d25ac6e2e310d999cf5462b3ed4f0d57c2906))
- Update .gitignore ([#19](https://github.com/zen-xu/plan_d/issues/19)) - ([1e95fec](https://github.com/zen-xu/plan_d/commit/1e95fec6b4694185e9067252ceb823e05a216f38))
- Update project metadata ([#1](https://github.com/zen-xu/plan_d/issues/1)) - ([64de6d9](https://github.com/zen-xu/plan_d/commit/64de6d96829e2ddeebe0f77eeef9ca7b914578c7))

### Build

- Rich no longer optional ([#18](https://github.com/zen-xu/plan_d/issues/18)) - ([83c54b2](https://github.com/zen-xu/plan_d/commit/83c54b25e5ba5f8f9f8cef6d8f433e279f1b2f40))
- Pin ipython=^8, prompt-toolkit=^3 ([#5](https://github.com/zen-xu/plan_d/issues/5)) - ([29050a4](https://github.com/zen-xu/plan_d/commit/29050a46ea25a52ba775e077c831b14c9fea909a))

<!-- generated by git-cliff -->
