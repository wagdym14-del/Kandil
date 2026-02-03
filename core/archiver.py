    async def analyze_and_archive(self, wallet: str, raw_data: dict, behavior_tag: str):
        """
        تحليل البصمة مع ضمان استخراج روابط الصور والأسماء بمرونة عالية.
        """
        risk_score = self._compute_risk_score(behavior_tag)
        now = datetime.datetime.utcnow().isoformat()
        
        # تحويل البيانات بالكامل لـ JSON للحفظ الدائم
        metadata_json = json.dumps(raw_data)

        # استخراج بيانات الـ API المبعوثة من السنيفر
        api_info = raw_data.get("api") or {}
        
        # [تعديل الجودة]: منطق مرن لجلب رابط الصورة والاسم لضمان عدم ضياعهم
        # يبحث الكود عن الصورة في الحقول المحتملة (image_url أو image_uri)
        token_image = api_info.get("image_url") or api_info.get("image_uri") or api_info.get("logo")
        token_name = api_info.get("name", "Scanning...")
        token_symbol = api_info.get("symbol", "-")

        self._cache[wallet] = {
            "tag": behavior_tag, 
            "threat": risk_score, 
            "coin_info": {
                "name": token_name,
                "symbol": token_symbol,
                "image": token_image
            }
        }

        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO mm_intel (wallet_id, threat_level, behavior_pattern, trust_score, total_raids, historical_data_json, last_seen_at)
                    VALUES (?, ?, ?, ?, 1, ?, ?)
                    ON CONFLICT(wallet_id) DO UPDATE SET
                        total_raids = total_raids + 1,
                        threat_level = (threat_level + ?) / 2,
                        behavior_pattern = excluded.behavior_pattern,
                        historical_data_json = excluded.historical_data_json,
                        last_seen_at = excluded.last_seen_at
                """, (wallet, risk_score, behavior_tag, 100-risk_score, metadata_json, now, risk_score))
                await db.commit()
                logger.info(f"💾 [SAVED] {behavior_tag} (with Intelligent Metadata) -> {wallet[:8]}")
        except Exception as e:
            logger.error(f"❌ Database Write Error: {e}")
