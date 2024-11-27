import openai
import pandas as pd
import csv
import src.config.keys as keys

api_key = keys.open_ai_key

data = pd.read_csv('ticks_data.csv')

batch = data.head(5).to_dict(orient='records')

def construct_prompt(batch):
    prompt = "Analyze the following climbing routes. For each route, provide:\n"
    prompt += "- Tags: Key classifications such as 'dihedral,' 'crack-climb,' 'face-climb,' etc.\n"
    prompt += "- Sentiment Analysis: Summarize the general sentiment about this route based on the description and comments in 1-3 sentences.\n\n"
    for idx, row in enumerate(batch, 1):
        prompt += f"Route {idx}:\n[START]\n"
        prompt += f"Name: {row['route_name']}\n"
        prompt += f"URL: {row['route_url']}\n"
        prompt += f"Description: {row['description']}\n"
        prompt += f"Comments: {row['comments']}\n[END]\n\n"
    return prompt

prompt = construct_prompt(batch)

try:

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an expert climbing route analyzer."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1500,
        temperature=0.6
    )

    output_text = response.choices[0].message.content

    print("GPT-4 Response:\n", output_text)

    # Step 6: Parse GPT-4 Response into a Data Structure
    results = []
    for idx, row in enumerate(batch, 1):
        result = {
            "route_name": row["route_name"],
            "route_url": row["route_url"],
            "tags": None,
            "sentiment_analysis": None
        }
        # Find the corresponding route response in GPT-4 output
        route_output = output_text.split(f"Route {idx}:")[1].split(f"Route {idx+1}:")[0] if idx < len(batch) else output_text.split(f"Route {idx}:")[1]
        
        # Extract tags and sentiment
        if "Tags:" in route_output:
            result["tags"] = route_output.split("Tags:")[1].split("Sentiment Analysis:")[0].strip()
        if "Sentiment Analysis:" in route_output:
            result["sentiment_analysis"] = route_output.split("Sentiment Analysis:")[1].strip()
        
        results.append(result)

    # Step 7: Write Results to a New CSV
    output_file = 'route_analysis.csv'
    with open(output_file, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    print(f"Results saved to {output_file}")

except Exception as e:
    print(f"Error: {e}")
