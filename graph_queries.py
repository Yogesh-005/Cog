"""
Graph Query Helper Module
Extract specific information from graph structure
"""
from collections import deque

def find_concept_relationships(graph_data, concept):
    """
    Find all relationships for a specific concept
    
    Args:
        graph_data: Dict with 'nodes' and 'edges'
        concept: Concept string to search for
    
    Returns:
        List of (concept1, relation, concept2) tuples
    """
    concept_id = concept.lower().replace(' ', '_')
    edges = graph_data.get('edges', [])
    nodes = graph_data.get('nodes', [])
    
    relationships = []
    
    for edge in edges:
        source = edge.get('source', '')
        target = edge.get('target', '')
        relation = edge.get('label', 'related')
        
        if source == concept_id or target == concept_id:
            source_label = get_node_label(source, nodes)
            target_label = get_node_label(target, nodes)
            relationships.append((source_label, relation, target_label))
    
    return relationships

def find_path_between_concepts(graph_data, concept1, concept2):
    """
    Find shortest path between two concepts using BFS
    
    Args:
        graph_data: Dict with 'nodes' and 'edges'
        concept1: Starting concept
        concept2: Ending concept
    
    Returns:
        List representing path, or None if no path found
    """
    concept1_id = concept1.lower().replace(' ', '_')
    concept2_id = concept2.lower().replace(' ', '_')
    
    nodes = graph_data.get('nodes', [])
    edges = graph_data.get('edges', [])
    
    # Check if both concepts exist
    node_ids = {n['id'] for n in nodes}
    if concept1_id not in node_ids or concept2_id not in node_ids:
        return None
    
    # Build adjacency list
    graph = {}
    edge_labels = {}
    
    for edge in edges:
        source = edge.get('source', '')
        target = edge.get('target', '')
        label = edge.get('label', 'related')
        
        if source not in graph:
            graph[source] = []
        if target not in graph:
            graph[target] = []
        
        graph[source].append(target)
        graph[target].append(source)  # Undirected
        
        edge_labels[(source, target)] = label
        edge_labels[(target, source)] = label
    
    # BFS to find shortest path
    queue = deque([(concept1_id, [concept1_id])])
    visited = {concept1_id}
    
    while queue:
        current, path = queue.popleft()
        
        if current == concept2_id:
            # Found path, format with labels
            formatted_path = []
            for i in range(len(path)):
                node_label = get_node_label(path[i], nodes)
                formatted_path.append(node_label)
                
                if i < len(path) - 1:
                    edge_key = (path[i], path[i+1])
                    relation = edge_labels.get(edge_key, 'related')
                    formatted_path.append(f"[{relation}]")
            
            return formatted_path
        
        # Explore neighbors
        for neighbor in graph.get(current, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor]))
    
    return None  # No path found

def get_concept_neighbors(graph_data, concept, hops=1):
    """
    Get all concepts within N hops of the given concept
    
    Args:
        graph_data: Dict with 'nodes' and 'edges'
        concept: Starting concept
        hops: Number of hops (default 1)
    
    Returns:
        List of (neighbor_concept, relationship, distance) tuples
    """
    concept_id = concept.lower().replace(' ', '_')
    nodes = graph_data.get('nodes', [])
    edges = graph_data.get('edges', [])
    
    # Build adjacency list
    graph = {}
    edge_labels = {}
    
    for edge in edges:
        source = edge.get('source', '')
        target = edge.get('target', '')
        label = edge.get('label', 'related')
        
        if source not in graph:
            graph[source] = []
        if target not in graph:
            graph[target] = []
        
        graph[source].append(target)
        graph[target].append(source)
        
        edge_labels[(source, target)] = label
        edge_labels[(target, source)] = label
    
    # BFS with distance tracking
    neighbors = []
    queue = deque([(concept_id, 0)])
    visited = {concept_id}
    
    while queue:
        current, dist = queue.popleft()
        
        if dist >= hops:
            continue
        
        for neighbor in graph.get(current, []):
            if neighbor not in visited:
                visited.add(neighbor)
                relation = edge_labels.get((current, neighbor), 'related')
                neighbor_label = get_node_label(neighbor, nodes)
                neighbors.append((neighbor_label, relation, dist + 1))
                queue.append((neighbor, dist + 1))
    
    return neighbors

def summarize_graph_for_concept(graph_data, concept):
    """
    Create human-readable summary for a concept
    
    Args:
        graph_data: Dict with 'nodes' and 'edges'
        concept: Concept to summarize
    
    Returns:
        String summary
    """
    relationships = find_concept_relationships(graph_data, concept)
    
    if not relationships:
        return f"No relationships found for '{concept}' in the knowledge graph."
    
    lines = [f"Knowledge about '{concept.capitalize()}':\n"]
    
    for source, relation, target in relationships[:10]:  # Limit to 10
        lines.append(f"  • {source} --[{relation}]--> {target}")
    
    if len(relationships) > 10:
        lines.append(f"  ... and {len(relationships) - 10} more relationships")
    
    return "\n".join(lines)

def get_node_label(node_id, nodes):
    """Helper to get readable label for a node ID"""
    for node in nodes:
        if node.get('id') == node_id:
            return node.get('label', node_id)
    return node_id.replace('_', ' ').title()

def extract_concepts_from_question(question, known_concepts):
    """
    Extract concept keywords from question
    
    Args:
        question: User's question
        known_concepts: List of concepts from the story
    
    Returns:
        List of concepts mentioned in question
    """
    question_lower = question.lower()
    mentioned = []
    
    for concept in known_concepts:
        if concept.lower() in question_lower:
            mentioned.append(concept)
    
    return mentioned