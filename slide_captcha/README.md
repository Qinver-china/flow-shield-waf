# 滑动验证静态素材

本目录挂载到 Docker 容器内 `/data/slide_captcha`，**可直接在此增删图片，无需重建镜像**（下次发题时自动读取）。

```
slide_captcha/
├── backgrounds/     # 背景图（JPG/PNG/WebP）
└── tiles/           # 拼图块（每组需 tile.png / tile-shadow.png / tile-mask.png）
    ├── tile-1/
    └── ...
```

## 背景图 `backgrounds/`

将 **10–20 张**背景图放入此目录，签发挑战时随机选取。

| 项目 | 建议 |
|------|------|
| 格式 | JPG / PNG / WebP |
| 尺寸 | 宽 ≥ 320px，高 ≥ 220px（推荐 400×240 或 16:9） |
| 内容 | 风景、建筑等细节丰富、非纯色大面积的图片 |
| 避免 | 纯白/纯黑、强文字、人脸特写、涉敏内容 |

文件名任意，例如 `bg-01.jpg`、`landscape-02.webp`。

## 拼图块 `tiles/tile-N/`

每组目录需包含：

- `tile.png` — 拼图块
- `tile-shadow.png` — 阴影
- `tile-mask.png` — 遮罩

仓库已内置 4 组默认素材（来自 pi-captcha 示例）。一般无需修改拼图块，主要替换 `backgrounds/` 即可。

## Docker 映射

`docker-compose.yml` 中：

```yaml
volumes:
  - ./slide_captcha:/data/slide_captcha
```

环境变量 `SLIDE_CAPTCHA_ASSETS_DIR=/data/slide_captcha`（已在 compose 中配置）。

## 说明

- 背景图为空时，发题会回退到内置纯色占位图。
- 修改图片后保存即可，**不用重启容器**（每次发题重新加载目录）。
