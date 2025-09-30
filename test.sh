# запомним имя текущей ветки (у тебя: frappe_dev)
BR=frappe_dev

# создаём orphan-ветку с пустой историей
git checkout --orphan ${BR}_clean

# сброс индекса, добавляем всё заново с учётом .gitignore
git rm -r --cached . 2>/dev/null || true
git add .

# убедись, что ТЯЖЁЛЫЕ файлы не в индексе:
git status --porcelain | grep -E 'logs|private/backups|public/files|assets' || echo "OK: no runtime junk staged"

# коммитим
git commit -m "recreate branch without logs/assets history"

# переименуемся обратно в исходное имя ветки
git branch -M ${BR}
