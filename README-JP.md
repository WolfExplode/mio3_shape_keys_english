<p align="center">
  <a href="README.md">English</a> |
  <a href="README-JP.md">日本語</a>
</p>

# Mio3 Shape Keys

キャラクターモデリングに特化したシェイプキー管理統合ツールです。

## ダウンロード

https://addon.mio3io.com/

## ドキュメント

[Mio3 Shape Keys Ver3 Documentation (WIP)](https://addon.mio3io.com/#/ja/mio3shapekeys/)


## Ver3 で追加された主な機能

-   シェイプキーの形状同期・自動編集
-   シェイプキーを維持したモディファイア適用
-   異なるトポロジーに対応したシェイプキーの一括転送
-   左右のシェイプキーを作成
-   逆側のシェイプキーを作成
-   タグ付け
-   シェイプキー値のプリセット登録
-   グループ化機能（標準では「===」から始まるの名前のキーでグループ化）
-   グループ単位の移動とソート
-   複数選択システム
-   選択したキーの一括処理
-   未使用やエラー要因など特定の条件のキーを探す機能
-   シェイプキーのスムージング
-   シェイプを対称化
-   シェイプを左右反転
-   シェイプの移動量を反転
-   シェイプをコピー＆ペースト
-   しきい値以上動いていない頂点をクリア
-   シェイプキーをオブジェクトとして実体化
-   Basis に適用で崩れるまばたきなどのシェイプキーの保護や修復機能

## Ver2

Ver2 は [releases](https://github.com/mio3io/mio3_shape_keys/releases) からダウンロードできます。


## 変更履歴
version = "3.0.0-beta-20260315"
https://youtu.be/vK5ssYbRR2o

選択したシェイプキーからドライバーを削除する機能を追加
- アクティブ、選択中、またはすべてのシェイプキーからドライバーを削除する新しいオペレーターを追加。

[Transfer Properties を追加](https://github.com/WolfExplode/mio3_shape_keys_english/commit/08a26b8643530a09e708ecf5639c438badd04c75)
- Transfer Shape Key ダイアログに Transfer Properties オプションを追加（ミュート、スライダー範囲、頂点グループ、タグ、コンポーザールール）。

[Transfer を最適化](https://github.com/WolfExplode/mio3_shape_keys_english/commit/3df7a487d14fda53a59486bdcfe647b3497fecd6)
- ベクトル化された補間、scipy cKDTree フォールバック、バッファ再利用、行列の事前計算。大きなメッシュで約60%高速化。

[Transfer Properties オペレーターを追加](https://github.com/WolfExplode/mio3_shape_keys_english/commit/909662d7b383b003dd79630e94ae5847b15b0604)
- シェイプキー名が一致する2つのオブジェクト用のスタンドアロン Transfer Properties オペレーター。

[Transfer Shape Key オペレーターを追加](https://github.com/WolfExplode/mio3_shape_keys_english/commit/7b92102b26e9e012bf0bad162ba0750fe81ce05a)
- シェイプキー名に従ってドライバーを転送

[「Set Value To Zero」オペレーターを追加](https://github.com/WolfExplode/mio3_shape_keys_english/commit/9e1b6ea22cf99bc06eabd21c2f55356f9bdfbdd8)
- 選択したシェイプキーの値をゼロに設定

[選択したシェイプキーから頂点グループを作成するオペレーターを追加](https://github.com/WolfExplode/mio3_shape_keys_english/commit/41536d34ffc962b8293f53d767f7d4df8a16eff6)

[シェイプキープリセットを拡張](https://github.com/WolfExplode/mio3_shape_keys_english/commit/aecbc7b3d1353c7a355086a92562d2bdd90db410)
シェイプキープリセットで一部のシェイプキーが保存されない問題を修正
オプションを追加：
- 選択したシェイプキーのみ使用
- ゼロ値のシェイプキーを含める

#### その他の変更：
- 「使用されているキーのみを表示」でシェイプキーグループも表示されるようになり、グループの展開・折りたたみが可能に
- グループの展開・折りたたみ用の三角をクリックすると、そのグループヘッダーがアクティブなシェイプキーに設定され、リストがクリックしたグループにフォーカスを維持
