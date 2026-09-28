# npm 发布

包名：`hermes-gtd-plugin`；本次版本：`2.3.0`；公开发布到 npm 官方 registry。
`package.json` 与 `plugin.yaml` 的版本必须一致，`prepack` 会验证。

在仓库根目录验证并生成发布文件：

```bash
npm test
mkdir -p dist
npm pack --pack-destination dist
npm publish ./dist/hermes-gtd-plugin-2.3.0.tgz --dry-run --access public
```

包采用文件白名单，只包含插件运行代码、GTD skill、网页静态文件、说明和许可证。
不包含历史 Claude 插件、测试数据、开发工具配置、Git/Jujutsu 元数据或凭证。
包无 npm 运行依赖和安装生命周期脚本；不会在安装时写入 Hermes 或 GTD 数据。

发布前用 `npm whoami --registry=https://registry.npmjs.org/` 检查身份。
若返回 401，先执行 `npm login --registry=https://registry.npmjs.org/`，按 npm 提示完成认证。
dry-run 不验证账户是否最终有权发布；包名未找到也不保证该名称可注册。

确认身份后，最后一步由发布者手动执行（可能需要浏览器或一次性验证码）：

```bash
npm publish ./dist/hermes-gtd-plugin-2.3.0.tgz --access public --registry=https://registry.npmjs.org/
```

发布使用已验证的 tarball。若更改任何发布文件，应重新打包和验证，不沿用旧 tarball。
发布后可用 `npm view hermes-gtd-plugin@2.3.0 version dist.integrity` 检查 registry 记录。
