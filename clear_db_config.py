import sqlite3

conn = sqlite3.connect('/app/data/inspirations.db')
cursor = conn.cursor()

print('🧹 Clearing API configurations from database...')

cursor.execute('UPDATE user_preferences SET openai_base_url = "", openai_api_key = NULL, openai_model = "", deepgram_api_key = "" WHERE id = 1')
conn.commit()

print('✅ Configurations cleared!')
print('')

cursor.execute('SELECT openai_base_url, openai_model, openai_api_key, deepgram_api_key FROM user_preferences WHERE id = 1')
result = cursor.fetchone()

print('📊 Verification:')
print(f'  openai_base_url = "{result[0]}"')
print(f'  openai_model = "{result[1]}"')
print(f'  openai_api_key = {result[2]}')
print(f'  deepgram_api_key = "{result[3]}"')
print('')
print('✅ All values are empty - backend will use .env defaults')

conn.close()
